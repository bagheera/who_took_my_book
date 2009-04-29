from google.appengine.api import memcache
from wtmb import *
import logging

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

line_break = "<br />"

###################################################################
class CacheBookIdsBorrowed:
    @classmethod
    def key(cls, user):
        return "book_ids_borrowed_by_" + user

    @classmethod
    def get(cls, user):
      books = memcache.get(cls.key(user))
      if not books:
        #TODO  should be a better way of doing this - not fetch each full book from db
        books = [str(book.key()) for book in AppUser.get(user).books_borrowed]
        logging.info("cbb books " + str(books))
        memcache.set(cls.key(user), books)
      return books

    @classmethod
    def reset(cls, user):
        logging.info("Reset CacheBookIdsBorrowed for " + AppUser.get(user).display_name())
        memcache.delete(cls.key(user))
#########################################################
class CacheBookIdsOwned:
    @classmethod
    def key(cls, owner):
        return "book_ids_owned_by_" + owner

    @classmethod
    def get(cls, owner):
      books_owned = memcache.get(cls.key(owner))
      if not books_owned:
        #TODO  should be a better way of doing this - not fetch each full book from db
        books_owned = [str(book.key()) for book in AppUser.get(owner).books_owned]
        logging.info("cbo books " + str(books_owned))
        memcache.set(cls.key(owner), books_owned)
      return books_owned

    @classmethod
    def reset(cls, owner):
        logging.info("Reset CacheBookIdsOwned for " + AppUser.get(owner).display_name())
        memcache.delete(cls.key(owner))
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
def before_change(book):
    if book.is_lent():
        CacheBookIdsBorrowed.reset(str(book.borrower.key()))

def after_change(book):
    owners_books = CacheBookIdsOwned.get(str(book.owner.key()))
    if not str(book.key()) in owners_books: #was it just created?
        CacheBookIdsOwned.reset(str(book.owner.key()))
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
