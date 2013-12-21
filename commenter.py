"""
A simple framework for building Reddit bots that reply to
submissions and comments in specific subreddits or multireddits.

Basic support is included for dynamic reply templating.

Uses Flask-style "routing", with decorators.
"""

import random, time, re, os
from functools import wraps

import praw
import yaml
import requests


class CommentBot(object):
    def __init__(self, words="words.yaml", **config):
        """
        `config` will be loaded from config.yaml or
        kwargs containing (user_agent, username, password)
        """
        self.r = self._load_config(**config)
        self.words = self._load_words(words)

        self._func_mapping = {}
        self.comments = self._init_comment_repliers()
        self.submissions = self._init_submission_repliers()
        self.already_replied = set()

    def _load_config(self, **config):
        if not config:
            with open("config.yaml") as f:
                config = yaml.load(f)

        self.logfile = config.get("log", "bot.log")
        if self.logfile and not os.path.exists(self.logfile):
            # Create the log file
            with open(self.logfile, "w"):
                pass

        r = praw.Reddit(config["user_agent"])
        r.login(config["username"], config["password"])
        return r

    def _load_words(self, fname):
        """A YAML file containing """
        with open(fname) as f:
            return FormatDict(yaml.load(f))

    def _log(self, msg):
        msg = msg.encode("ascii", "replace")
        if not self.logfile:
            print msg
        else:
            with open(self.logfile, "a") as f:
                f.write(msg + "\n")

    def _set_replier(self, pool):
        """A decorator factory for providing Flask-like route decorators."""
        def _factory(subreddit, listing="rising", only=lambda c: True):
            def _add_to_repliers(func):
                @wraps(func)
                def _wrapped(content):
                    args = [None]
                    ret = func(content)

                    if not ret or isinstance(ret, basestring):
                        # Default case
                        msg = ret
                    else:
                        # Additional options specified, like postprocessing or sub-keys
                        msg, args = ret
                    if isinstance(args, dict):
                        return self._permute_message(msg, subreddit, **args)
                    else:
                        return self._permute_message(msg, subreddit, *args)

                sub = self.r.get_subreddit(subreddit)
                pool.append((sub, (_wrapped, listing, only)))
                random.shuffle(pool)
                return _wrapped
            return _add_to_repliers
        return _factory

    def _init_comment_repliers(self):
        comment_repliers = []
        self._func_mapping[self._reply_to_comments] = comment_repliers
        return self._set_replier(comment_repliers)

    def _init_submission_repliers(self):
        submission_repliers = []
        self._func_mapping[self._reply_to_submissions] = submission_repliers
        return self._set_replier(submission_repliers)

    def _add_comment(self, content, comment):
        if isinstance(content, praw.objects.Submission):
            return content.add_comment(comment)
        else:
            return content.reply(comment)

    def _make_comment(self, content, comment):
        if not content or content.id in self.already_replied or not comment:
            return "**[SKIPPED DUE TO UNSUITABLE CONTENT SELECTION]**"

        while True:
            # Loop to re-try commenting if rate limit is hit
            try:
                self._add_comment(content, comment)
                self.already_replied.add(content.id)
                return comment
            except praw.errors.RateLimitExceeded as e:
                self._log("[RATE LIMITED] Sleeping %d seconds...\n" % e.sleep_time)
                time.sleep(e.sleep_time)
            except praw.errors.APIException as e:
                self._log("[API Error] %s\n" % e)
                return "**[SKIPPED DUE TO API ERROR]**"
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    subreddit = content.subreddit.display_name
                    self._log("!!![BANNED FROM SUBREDDIT: %s]!!!" % subreddit)
                    self._remove_subreddit(subreddit)
                    return "**[SKIPPED DUE TO BAN: REMOVED SUBREDDIT]**"
                else:
                    return "**[SKIPPED DUE TO UNKNOWN HTTP ERROR]**"
            except Exception as e:
                self._log("**[EXCEPTION] %s\n" % e)
                return "**[SKIPPED DUE TO UNKNOWN EXCEPTION]**"

    def _remove_subreddit(self, subreddit):
        for func in self._func_mapping:
            repliers = self._func_mapping[func]
            self._func_mapping[func] = [r for r in repliers if r[0].display_name != subreddit]

    def _permute_message(self, msg, subreddit, postprocess=None, key=None):
        """
        Uses words.yaml to fill in reply templates.

        By default, looks in words["subredditname"].
        If `key` is a string, it will look in words["subredditname"][key].
        If `key` is a sequence, it will look in words[key[0][key[...n]] instead.
        """
        if not msg:
            return

        if key:
            selections = traverse_dict(self.words, subreddit, key)
        else:
            selections = self.words[subreddit]

        # Hacky, but necessary to handle "{key1} {key2}" cases
        categories = re.findall(r"{(\w+)}", msg)
        if categories:
            if not selections:
                raise KeyError("No entry for '%s' in YAML file" % subreddit)
            choices = {k: random.choice(selections[k]) for k in categories}
            msg = msg.format(**choices)

        if postprocess:
            return postprocess(msg)

        return msg

    def _reply_to_comments(self, subreddit, replier, listing, only):
        # `listing` not yet implemented here
        comments = filter(only, subreddit.get_comments())
        comment = random.choice(comments) if comments else None
        return self._make_comment(comment, replier(comment))

    def _reply_to_submissions(self, subreddit, replier, listing, only):
        submissions = filter(only, praw.internal._get_sorter(listing)(subreddit))
        submission = random.choice(submissions) if submissions else None
        return self._make_comment(submission, replier(submission))

    def reply_to_all(self):
        for func, repliers in self._func_mapping.iteritems():
            for subreddit, (replier, listing, only) in repliers:
                yield subreddit, func(subreddit, replier, listing, only)
                time.sleep(3)

    def run(self, verbose=False):
        while True:
            for subreddit, comment in self.reply_to_all():
                if verbose:
                    self._log("%s :: %s" % (subreddit, comment))
                    self._log("\n%s\n" % ("#" * 60))

## Filter functions to be passed as `only` keyword argument
## Example:
##
## @bot.comments("subreddit", only=contains("some phrase"))
## Searches only for comments containing "some phrase" in them

def min_length(n):
    @wraps(min_length)
    def _wrapped(content):
        return len(content.body) >= n
    return _wrapped

def contains(s):
    @wraps(contains)
    def _wrapped(content):
        return s in content.body.lower().split()
    return _wrapped

## Utility classes and functions

class FormatDict(dict):
    """
    For use in reply formatting from words.yaml. Allows dct['key1'] and
    dct['keyN'] to return dct['key']. This allows templates like
    "{verb1} a {noun1} and {verb2} a {noun2}".
    """
    def __getitem__(self, key):
        if key[-1].isdigit():
            key = key[:-1]
        result = dict.get(self, key.lower())
        if isinstance(result, dict):
            result = FormatDict(result)
        return result

def traverse_dict(d, start, key):
    if isinstance(key, basestring):
        return d[start][key]

    for s in key:
        d = d[key]
    return d
