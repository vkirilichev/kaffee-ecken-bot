#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# KaffeeEckenBot

from datetime import datetime
from lxml import html
from pymongo import MongoClient
from telegram.ext import Updater, Job, Filters, CommandHandler, MessageHandler, RegexHandler

import logging
import os
import requests
import sys
import telegram

PHOTO_CNT = 2 # Default number of sent photos starting from 0

DOMAIN = "https://www.kaffee-netz.de"
forum = {
    "Kaffee-Ecken": "threads/wie-sieht-eure-kaffee-ecke-aus.13966",
    "Kaffeekram": "threads/der-ich-habe-gerade-kaffeekram-gekauft-thread.62180",
    "Latte-Art": "threads/und-ploetzlich-war-da-latte-art.7785",
    "Espresso": "threads/ich-trinke-gerade-diesen-espresso.19308"
}

_db = MongoClient(host='db', port=27017).KaffeeEckenBot


# Enable logging
logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)

logger = logging.getLogger(__name__)


def lookahead(iterable):
    """
    Pass through all values from the given iterable, augmented by the
    information if it is the last value (True),
    or there are more values to come after the current one (False).
    """
    it = iter(iterable)
    last = next(it)
    for val in it:
        yield last, False
        last = val
    yield last, True


"""
Commands
"""
def start(bot, update):
    bot.sendMessage(update.message.chat_id, text='Hi, I’m KaffeeEckenBot, an assistant for kaffee-netz.de.')
    bot.sendMessage(update.message.chat_id, text='Let’s get started. What news are you interested in?', reply_markup = _getInitMarkup())


def unknown(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text='''I’m sorry, I cannot answer you any questions.''')


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


"""
Non-commands
"""
def subscribe(bot, update):
    session = _getSession(update.message.chat_id)
    if session is not None:
        url = session['url']
        _startSubscription(update.message.chat_id, url)
        bot.sendMessage(update.message.chat_id, 'Successfully subscribed to "{}/{}"'.format(DOMAIN, url), reply_markup = _getMainMarkup(update.message.chat_id, url))
    else:
        bot.sendMessage(update.message.chat_id, 'No active session found, select a menu option.', reply_markup = _getInitMarkup())


def unsubscribe(bot, update):
    session = _getSession(update.message.chat_id)
    if session is not None:
        url = session['url']
        subscription = _getSubscription(update.message.chat_id, url)
        if subscription is not None:
            url = subscription['url']
            _removeSubscription(update.message.chat_id, url)
            bot.sendMessage(update.message.chat_id, 'Successfully unsubscribed from "{}/{}"'.format(DOMAIN, url), reply_markup = _getMainMarkup(update.message.chat_id, url))
        else:
            bot.sendMessage(update.message.chat_id, 'No subscription found, select a menu option.', reply_markup = _getInitMarkup())
    else:
        bot.sendMessage(update.message.chat_id, 'No active session found, select a menu option.', reply_markup = _getInitMarkup())


def kaffeeEcken(bot, update):
    url = forum["Kaffee-Ecken"]
    _startSession(update.message.chat_id, url)
    _sendLastPosts(bot, url, PHOTO_CNT, 0, update.message.chat_id, _getMainMarkup(update.message.chat_id, url))

def kaffeekram(bot, update):
    url = forum["Kaffeekram"]
    _startSession(update.message.chat_id, url)
    _sendLastPosts(bot, url, PHOTO_CNT, 0, update.message.chat_id, _getMainMarkup(update.message.chat_id, url))

def latteArt(bot, update):
    url = forum["Latte-Art"]
    _startSession(update.message.chat_id, url)
    _sendLastPosts(bot, url, PHOTO_CNT, 0, update.message.chat_id, _getMainMarkup(update.message.chat_id, url))

def espresso(bot, update):
    url = forum["Espresso"]
    _startSession(update.message.chat_id, url)
    _sendLastPosts(bot, url, PHOTO_CNT, 0, update.message.chat_id, _getMainMarkup(update.message.chat_id, url))


def morePosts(bot, update):
    session = _getSession(update.message.chat_id)
    if session is not None:
        url = session['url']
        skip = session['skip']
        skip += PHOTO_CNT + 1
        _db.session.update({'_id': session['_id']}, {"$set": {"skip": skip}})
        _sendLastPosts(bot, url, PHOTO_CNT, skip, update.message.chat_id, _getMainMarkup(update.message.chat_id, url))
    else:
        bot.sendMessage(update.message.chat_id, 'No active session found, select a menu option.', reply_markup = _getInitMarkup())


def back(bot, update):
    bot.sendMessage(update.message.chat_id, 'Select a menu option.', reply_markup = _getInitMarkup())


def _getInitMarkup():
        return telegram.ReplyKeyboardMarkup(keyboard = [
                [
                    telegram.KeyboardButton(text='Kaffee-Ecken'),
                    telegram.KeyboardButton(text='Kaffeekram'),
                    telegram.KeyboardButton(text='Latte-Art'),
                    telegram.KeyboardButton(text='Espresso')
                ]
            ])

def _getMainMarkup(chat_id, url):
    subscription = _getSubscription(chat_id, url)
    if subscription is None:
        return telegram.ReplyKeyboardMarkup(keyboard = [
            [ telegram.KeyboardButton(text='Subscribe'), telegram.KeyboardButton(text='More Posts') ],
            [ telegram.KeyboardButton(text='↩︎ Back')]
        ])
    else:
        return telegram.ReplyKeyboardMarkup(keyboard = [
            [ telegram.KeyboardButton(text='Unsubscribe'), telegram.KeyboardButton(text='More Posts') ],
            [ telegram.KeyboardButton(text='↩︎ Back')]
        ])


def _startSession(chat_id, url):
    _db.session.insert_one({"chat_id": chat_id, "url": url, "skip": 0})

def _getSession(chat_id):
    cursor = _db.session.find({"chat_id": chat_id}).sort([('_id', -1)]).limit(1)
    for session in cursor:
        return session
    return None


def _startSubscription(chat_id, url):
    _db.subscription.insert_one({"chat_id": chat_id, "url": url, "date": datetime.now(), "last_msg": datetime.now()})

def _getSubscription(chat_id, url):
    cursor = _db.subscription.find({"chat_id": chat_id, "url": url}).sort([('_id', -1)]).limit(1)
    for subscription in cursor:
        return subscription
    return None

def _getSubscriptions(chat_id):
    return _db.subscription.find({"chat_id": chat_id}).sort([('_id', -1)])

def _removeSubscription(chat_id, url):
    _db.subscription.delete_many({"chat_id": chat_id, "url": url})


"""
Iterate through subscribers and send messages if necessary.
"""
def _sendNewsletter(bot, job):
    for topic, url in forum.items():
        # Step 1. Check updates
        logger.debug('Checking updates for "%s"..' % (topic))
        posts = _getLastPosts(url, PHOTO_CNT)

        # Step 2. Send updates
        cursor = _db.subscription.find({"url": url})
        for subscription in cursor:
            last_msg = subscription["last_msg"]
            chat_id = subscription["chat_id"]
            for post in posts:
                if last_msg < post["date"]:
                    _sendMessage(bot, chat_id, post)
                    _db.subscription.update({"_id": subscription["_id"]}, {"$set": {"last_msg": datetime.now()}})


def _sendLastPosts(bot, url, num, skip, chat_id, reply_markup=None):
    posts = _getLastPosts(url, num, skip)
    for post, isLast in lookahead(posts):
        _sendMessage(bot, chat_id, post, isLast, reply_markup)


def _sendMessage(bot, chat_id, post, isLast=False, reply_markup=None):
    if 'img' in post:
        bot.sendPhoto(chat_id, post['img'], post['url'], reply_markup = reply_markup if isLast else None)
    elif 'filename' in post:
        with open(post['filename'], 'rb') as f:
            post['file'] = f
            response = bot.sendPhoto(chat_id, f, post['url'], reply_markup = reply_markup if isLast else None)
            _db.img.insert_one({"url": post['img_url'], "photo": response['photo'][-1]["file_id"], "date": datetime.now()})
        os.remove(post['filename'])


"""
Get last _num_ posts with images in the specific topic.
If the image was already uploaded to the telegram servers, cached version will be returned.
"""
def _getLastPosts(url, num, skip=0):
    page = requests.get("{}/{}".format(DOMAIN, url))
    tree = html.fromstring(page.text)
    details = tree.xpath('.//a[contains(@href, "{}/page")]'.format(url))[-2]
    pageNumber = int(details.text_content())

    posts = []

    def _processPage(posts, pageNumber):
        last_page = requests.get("{}/{}/page-{}".format(DOMAIN, url, pageNumber))
        tree = html.fromstring(last_page.text)
        images = tree.xpath("//img[contains(@class, 'LbImage')]")
        for img in reversed(images):
            _direct_parent = img.getparent()
            # skip quoted posts
            if _direct_parent.attrib['class'] != u'quote':
                if _direct_parent.attrib['class'] == u'LbTrigger':
                    img = _direct_parent
                    _direct_parent = _direct_parent.getparent()
                if _direct_parent.attrib['class'] == u'externalLink':
                    _direct_parent = _direct_parent.getparent()
                if _direct_parent.attrib['class'] == u'thumbnail':
                    # ignore thumbnails
                    continue
                post = {}
                _parent = _direct_parent.getparent().getparent().getparent().getparent().getparent()
                print(img.attrib)
                forum_post = _parent.xpath(".//a[contains(@class, 'postNumber')]")[0]
                post['url'] = "{}/{}".format(DOMAIN, forum_post.attrib['href'])

                if 'data-url' in img.attrib:
                    img_url = img.attrib['data-url']
                elif 'src' in img.attrib:
                    img_url = img.attrib['src']
                elif 'href' in img.attrib:
                    img_url = img.attrib['href']
                if not img_url.startswith('http'):
                    img_url = 'http:' + img_url if img_url.startswith('//') else DOMAIN + '/' + img_url
                cached_img = _db.img.find_one({"url": img_url})
                if cached_img:
                    post["img"] = cached_img["photo"]
                    post["date"] = cached_img["date"]
                else:
                    r = requests.get(img_url.split('[IMG]')[-1]) if '[IMG]' in img_url else requests.get(img_url)
                    if r.status_code == 200:
                        filename = img_url[:-1].split('/')[-1] if img_url.endswith('/') else img_url.split('/')[-1]
                        if not os.path.exists(filename):
                            with open(filename, 'wb') as f:
                                for chunk in r:
                                    f.write(chunk)
                        post['filename'] = filename
                        post['img_url'] = img_url
                        post["date"] = datetime.now()
                posts.append(post)
                if len(posts) > num + skip:
                    break
        return posts

    # if the last page doesn't contain the required amount of images, go to the previous page
    while len(posts) <= num + skip:
        _processPage(posts, pageNumber)
        pageNumber -= 1
        if pageNumber == 0:
            break
    return list(reversed(posts[skip:]))


def main():
    updater = Updater(sys.argv[1])
    job_queue = updater.job_queue

    dp = updater.dispatcher

    # Commands
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("start", start))

     # Non-commands
    dp.add_handler(RegexHandler(r"Subscribe", subscribe))
    dp.add_handler(RegexHandler(r"Unsubscribe", unsubscribe))

    dp.add_handler(RegexHandler(r"Kaffee-Ecken", kaffeeEcken))
    dp.add_handler(RegexHandler(r"Kaffeekram", kaffeekram))
    dp.add_handler(RegexHandler(r"Latte-Art", latteArt))
    dp.add_handler(RegexHandler(r"Espresso", espresso))

    dp.add_handler(RegexHandler(r"More Posts", morePosts))
    dp.add_handler(RegexHandler(r"↩︎ Back", back))

    dp.add_handler(RegexHandler(r'.*', unknown))

    # Errors
    dp.add_error_handler(error)

    # Subscriptions (once a hour)
    job_queue.put(Job(_sendNewsletter, 3600, repeat=True))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
