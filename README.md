reddit-commenter
===============

A very simple framework for writing reddit bots, using the PRAW API wrapper.

Specifically useful for writing bots that scan submissions or comments on one or more specified subreddits.

Rate limiting is handled automatically.

Included as an example is a downvote-accumulating bot called "AggravatingBot".

Configuration
=============

Use a `config.yaml` file, with a structure as follows:

    username: BOTUSERNAME
    password: BOTPASSWORD
    user_agent: BOTUSERAGENT
    log: FILENAME.log

Usage
=====

Similar to Flask, "routes" can be registered using decorators: `CommentBot.comments` and `CommentBot.submissions`.

For decorators that only specify subreddit names, a random "rising" submission, or a random new comment, will be selected in an infinite loop.

Here is all the code you need to write a bot.

    from commenter import CommentBot
    bot = CommentBot()
    
    @bot.submissions("iama")
    def iama(submission):
        return "Hi %s!" % submission.author.name
        
    @bot.comments("askreddit")
    def askreddit(comment):
        first_line = comment.body.splitlines()[0]
        return ">%s\n\nThat's cool, but one time..." % first_line
        
    bot.run()
    
All actions taken will be logged into the filename specified in the config.


Advanced Options
================

**Advanced content selection**

The `submissions` and `comments` decorators also optionally accept two additional parameters:

`listing` - Choose one of `"new"`, `"rising"`, `"hot"`, `"top"`, or `"controversial"`. Used only for submissions, not comments.

`only` - A function with which to filter content found in the listing. For example, to only reply to comments that are longer than 200 characters, one could write:

    @bot.comments("subredditname", only=lambda c: len(c.body) > 200)

Two convenience functions have already been provided for `only` filters: `min_length()` and `contains()`. The above could be rewritten as:

    @bot.comments("subredditname", only=min_length(200))
    
`contains()` can be used to only select content whose body contains certain text, case insensitive. For example, to only respond to new submissions that mention cats:

    @bot.submissions("subredditname", listing="new", only=contains("cat"))

**Multiple subreddits**
    
You can also scan multiple subreddits with one function by joining each subreddit name with `+`. For example:

    @bot.comments("iama+askreddit+funny")
    
**Reply templating**

Look at `words.yaml` in the example bot to see how to structure a template. Returning a string with `"{keyname}"` in it will choose a random string from the list whose key is `keyname`.

**Advanced replying**

Replying functions can optionally return a tuple of `(str, dict)`, where the dict contains a `key` and/or a `postprocessing` setting.

`key` - The dict to look up template string keys in. By default looks to `words.yaml` if this is not supplied.
`postprocessing` - A function to run on the return string after all templating has been applied.
