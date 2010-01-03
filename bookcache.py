from google.appengine.api import memcache
import logging
import urllib
from wtmb import Book
from eventregistry import MembershipChanged
###################################################################

class CacheBookIdsBorrowed:

    @classmethod
    def key(cls, user_key):
        return "book_ids_borrowed_by_" + str(user_key)

    @classmethod
    def get(cls, user_key):
      books = memcache.get(cls.key(user_key))
      if not books:
        books = set(str(book_key) for book_key in Book.borrowed_by(user_key))
        memcache.set(cls.key(user_key), books)
      return books

    @classmethod
    def reset(cls, str_user_key):
        logging.info("Reset CacheBookIdsBorrowed for " + AppUser.get(str_user_key).display_name())
        memcache.delete(cls.key(str_user_key))

    @classmethod
    def add_book(cls, user_key_str, book_key_str):
        cls.get(user_key_str); #just to make sure we have an entry
        user_key_mc = cls.key(user_key_str)
        book_set = memcache.get(user_key_mc)
        book_set.add(book_key_str)
        memcache.set(user_key_mc, book_set)

    @classmethod
    def remove_book(cls, user_key_str, book_key_str):
        book_set = cls.get(user_key_str)
        if book_set and book_key_str in book_set:
            book_set.remove(book_key_str)
            memcache.set(cls.key(user_key_str), book_set)
#########################################################
class CacheBookIdsOwned:
    @classmethod
    def key(cls, owner_key):
        return "book_ids_owned_by_" + str(owner_key)

    @classmethod
    def get(cls, owner_key):
      books_owned = memcache.get(cls.key(owner_key))
      if not books_owned:
        books_owned = set(str(book_key) for book_key in Book.owned_by(owner_key))
        memcache.set(cls.key(owner_key), books_owned)
      return books_owned

    @classmethod
    def reset(cls, str_owner_key):
        logging.info("Reset CacheBookIdsOwned for " + AppUser.get(str_owner_key).display_name())
        memcache.delete(cls.key(str_owner_key))

    @classmethod
    def add_book(cls, owner_key_str, book_key_str):
        cls.get(owner_key_str); #just to make sure we have an entry
        owner_key_mc = cls.key(owner_key_str)
        book_set = memcache.get(owner_key_mc)
        book_set.add(book_key_str)
        memcache.set(owner_key_mc, book_set)

    @classmethod
    def remove_book(cls, owner_key_str, book_key_str):
        book_set = cls.get(owner_key_str)
        if book_set and book_key_str in book_set:
            book_set.remove(book_key_str)
            memcache.set(cls.key(owner_key_str), book_set)
#########################################################
class CachedBook:
    @classmethod
    def key(cls, book_id):
        return "bookid_" + book_id

    @classmethod
    def get(cls, book_id):
        book = memcache.get(cls.key(book_id))
        if not book:
          book = Book.get(book_id).to_hash()
          memcache.set(cls.key(book_id), book)
        return book

    @classmethod
    def reset(cls, book_id):
        memcache.delete(cls.key(book_id))
        
    @classmethod
    def on_group_change(cls, info):
        affected_book_keys = CacheBookIdsOwned.get(info['owner_key'])
        for key in affected_book_keys:
            cachedBook = cls.get(key)
            cachedBook['owner_groups'] = ','.join(info['new_groups'])
            memcache.replace(cls.key(key), cachedBook)
#########################################################
feed_key = "feed/whats_new"
from datetime import datetime
import os
from google.appengine.ext.webapp import template
class CachedFeed:
    @staticmethod
    def get():
        feed = memcache.get(feed_key)
        if not feed:
            new_book_keys = [str(key_obj) for key_obj in Book.new_books()]
            new_books = [CachedBook.get(book_id) for book_id in new_book_keys]
            template_values = {
              'root': "http://whotookmybook.appspot.com/",
              'books': new_books,
              'updated_feed': datetime.now().isoformat() + 'Z'
            }
            path = os.path.join(os.path.dirname(__file__), 'whats_new.template')
            feed = template.render(path, template_values)
            memcache.set(feed_key, feed)
        return feed

    @staticmethod
    def reset():
        logging.info("Reset feed ")
        memcache.delete(feed_key)
#########################################################
MembershipChanged().subscribe(CachedBook.on_group_change)