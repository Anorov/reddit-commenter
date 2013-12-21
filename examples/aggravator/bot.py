#!/usr/bin/env python

"""
An aggravating Reddit bot.
Accumulates downvotes by making irritating replies to submissions and comments.
"""
import sys; sys.path.append("../..")
import random, string, re

import requests
from textblob import TextBlob

from commenter import CommentBot, min_length

bot = CommentBot()

def noun_phrases(s):
    """
    Extracts all noun-phrases from the string, using
    natural language processing.
    """
    return [n for n in TextBlob(s).noun_phrases if n.replace(" ", "").isalpha()]

def choose(*choices):
    return random.choice(choices)

@bot.comments("adviceanimals")
def adviceanimals_aggravate(comment):
    x = choose("x", "X")
    return "{literally}, {laughter} {dude} thats {adjective} {epic} %sD" % x

@bot.comments("fffffffuuuuuuuuuuuu", only=min_length(25))
def f7u12_aggravate(comment):
    nouns = noun_phrases(comment.body)
    if not nouns:
        return
    return u">{0}\n\n*le* {0}\n\nFTFY".format(random.choice(nouns))

@bot.submissions("iama", listing="new", only=lambda s: "request" not in s.title.lower())
def iama_aggravate(submission):
    choice = choose("rather", "statement")

    if choice == "rather":
        reply = "Would u rather {verb1} a {noun1} or {verb2} a {noun2}{punctuation}"
        return reply, {"key": choice}
    else:
        title = re.sub(r"\[?(?:i ?am ?a|ama|ask me (?:anything)?)\]?", "", submission.title, flags=re.I)
        title = [s for s in re.split("[%s]" % string.punctuation, title) if s][0].strip()
        nouns = noun_phrases(title)
        if not nouns:
            return
        noun = max(nouns, key=len)
        exclamations = "!" * random.randint(3, 9)
        reply = "{excitement} I {feel} %s%s" % (noun, exclamations)
        return reply, {"postprocess": lambda s: s.upper(), "key": choice}

@bot.submissions("todayilearned", listing="new")
def til_aggravate(submission):
    return "{uh} {yeah} this is {dumb} i knew that already.. plus repost."

#@bot.submissions("atheism", listing="new")
def atheism_aggravate(submission):
    msg = ("Heathens...... You are *All* Satanic, of The DEVIL. Quote from The Holy Bible, "
           "a real Text written by the LORD our God.\n\nPay Close attention %s..\n\n>%s\n")
    quote = requests.get("http://labs.bible.org/api/?passage=random").text
    quote = re.sub(r"</?b>", "**", quote)
    author = re.sub(r"\d", "", submission.author.name.lower())
    return msg % (author, quote)

@bot.submissions("funny", listing="new")
def funny_aggravate(submission):
    msg = "thats {funny1} {laughter1} {exclamation1} {laughter2} i mean jesus, thats {funny2} {exclamation2} {laughter3}{punctuation}"
    return msg, {"postprocess": lambda s: s.upper()}

@bot.submissions("music", listing="new")
def music_aggravate(submission):
    if choose(True, False):
        return "this is the wrst thing ive ever heard!!!!!"

    choice = choose("sucks", "meh")
    if choice == "sucks":
        msg = "{ugh} this band honestly sucks {animal} {noun}"
    else:
        msg = "{yeah} uh {bad}.. sorry...."
    return msg, {"key": choice}

if __name__ == "__main__":
    bot.run(verbose=True)
