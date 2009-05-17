from google.appengine.api import memcache
from wtmb import *
import logging
import urllib
###################################################################  
# global stuff
def post_process(f, after):
    def g(self, *args):
        f(self, *args)
        after(self)
    return g

def pre_process(f, before):
    def g(self, *args):
        before(self)
        f(self, *args)
    return g

###################################################################
class CacheBookIdsBorrowed:
    @classmethod
    def key(cls, user_key):
        return "book_ids_borrowed_by_" + str(user_key)

    @classmethod
    def get(cls, user_key):
      books = memcache.get(cls.key(user_key))
      if not books:
        books = [str(book_key) for book_key in Book.borrowed_by(user_key)]
        memcache.set(cls.key(user_key), books)
      return books

    @classmethod
    def reset(cls, str_user_key):
        logging.info("Reset CacheBookIdsBorrowed for " + AppUser.get(str_user_key).display_name())
        memcache.delete(cls.key(str_user_key))
#########################################################
class CacheBookIdsOwned:
    @classmethod
    def key(cls, owner_key):
        return "book_ids_owned_by_" + str(owner_key)

    @classmethod
    def get(cls, owner_key):
      books_owned = memcache.get(cls.key(owner_key))
      if not books_owned:
        books_owned = [str(book_key) for book_key in Book.owned_by(owner_key)]
        memcache.set(cls.key(owner_key), books_owned)
      return books_owned

    @classmethod
    def reset(cls, str_owner_key):
        logging.info("Reset CacheBookIdsOwned for " + AppUser.get(str_owner_key).display_name())
        memcache.delete(cls.key(str_owner_key))
#########################################################
class CachedBook:
    @classmethod
    def key(cls, book_id):
        return "bookid_" + book_id

    @classmethod
    def get(cls, book_id):
        book = memcache.get(cls.key(book_id))
        if not book:
          book = Book.get(book_id).to_json()
          memcache.set(cls.key(book_id), book)
        return book

    @classmethod
    def reset(cls, book_id):
        logging.info("Reset CachedBook " + Book.get(book_id).title)
        memcache.delete(cls.key(book_id))
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
            new_books = [simplejson.loads(CachedBook.get(book_id)) for book_id in new_book_keys]
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

def before_change(book):
    if book.is_lent():
        CacheBookIdsBorrowed.reset(str(book.borrower.key()))

def after_change(book):
    owners_books = CacheBookIdsOwned.get(str(book.owner.key()))
    if not str(book.key()) in owners_books: #was it just created?
        CacheBookIdsOwned.reset(str(book.owner.key()))
        CachedFeed.reset()
    else: #just changed hands?
        CachedBook.reset(str(book.key()))
        if book.is_lent():
          CacheBookIdsBorrowed.reset(str(book.borrower.key()))

def before_delete(book):
    if book.is_lent():
       CacheBookIdsBorrowed.reset(str(book.borrower.key()))
    CacheBookIdsOwned.reset(str(book.owner.key()))
    CachedBook.reset(str(book.key()))

Book.borrow = pre_process(Book.borrow, before_change)
Book.borrow = post_process(Book.borrow, after_change)

Book.lend_to = pre_process(Book.lend_to, before_change)
Book.lend_to = post_process(Book.lend_to, after_change)

Book.return_to_owner = pre_process(Book.return_to_owner, before_change)
Book.return_to_owner = post_process(Book.return_to_owner, after_change)

Book.obliterate = pre_process(Book.obliterate, before_delete)
Book.create = post_process(Book.create, after_change)
