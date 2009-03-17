from google.appengine.api import memcache
from wtmb import *
import logging

###################################################################  
# global stuff
def post_process(f, after):
    def g(self):
        f(self)
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
    def __init__(self, owner):
        self.owner = owner
        
    def key(self):
        return "book_ids_borrowed_by_" + self.owner
    
    def get(self):
      books_owned = memcache.get(self.key())  
      if not books_owned:
        #TODO  should be a better way of doing this - not fetch each full book from db
        books_owned = [book.key() for book in AppUser.get(self.owner).books_borrowed]
        memcache.set(self.key(), books_owned)
      return books_owned
  
    def reset(self):
        logging.info("Reset CacheBookIdsBorrowed for "+ self.owner)
        memcache.delete(self.key())

class CacheBookIdsOwned:
    def __init__(self, owner):
        self.owner = owner
        
    def key(self):
        return "book_ids_owned_by_" + self.owner
    
    def get(self):
      books_owned = memcache.get(self.key())  
      if not books_owned:
        #TODO  should be a better way of doing this - not fetch each full book from db
        books_owned = [book.key() for book in AppUser.get(self.owner).books_owned]
        memcache.set(self.key(), books_owned)
      return books_owned

    def reset(self):
        logging.info("Reset CacheBookIdsOwned for "+ self.owner)
        memcache.delete(self.key())

class CacheTechBookIdsOwned:
    def __init__(self, owner):
        self.owner = owner
        
    def technical(self, book):
      return book.is_technical
  
    def key(self):
        return "tech_book_ids_owned_by_" + self.owner
    
    def get(self):
      books_owned = memcache.get(self.key())  
      if not books_owned:
        #TODO  should be a better way of doing this - not fetch each full book from db
        books_owned = [book.key() for book in filter(self.technical, AppUser.get(self.owner).books_owned)]
        memcache.set(self.key(), books_owned)
      return books_owned

    def reset(self):
        logging.info("Reset CacheTechBookIdsOwned for "+ self.owner)
        memcache.delete(self.key())

class CacheListingForOwner:
    def __init__(self, book_id):
        self.book_id = book_id
        
    def key(self):
        return "owner_of_bookid_" + self.book_id
    
    def get(self):
        book_listing = memcache.get(self.key())
        if not book_listing:
          book = Book.get(self.book_id)
          book_listing = book.summary_loan()
          book_listing += book.transitions()
          book_listing += line_break
          memcache.set(self.key(), book_listing)
        return book_listing

    def reset(self):
        logging.info("Reset CacheListingForOwner "+ self.book_id)
        memcache.delete(self.key())

class CacheListingForViewer:
    def __init__(self, book_id):
        self.book_id = book_id
        
    def key(self):
        return "viewer_of_bookid_" + self.book_id
    
    def get(self):
        book_listing = memcache.get(self.key())
        if not book_listing:
          book = Book.get(self.book_id)
          book_listing = book.summary_loan()
          book_listing += book.transition_if_borrowable()
          book_listing += line_break
          memcache.set(self.key(), book_listing)
        return book_listing

    def reset(self):
        logging.info("Reset CacheListingForViewer "+ self.book_id)
        memcache.delete(self.key())

class CacheListingForBorrower:
    def __init__(self, book_id):
        self.book_id = book_id
        
    def key(self):
        return "borrower_of_bookid_" + self.book_id
    
    def get(self):
        book_listing = memcache.get(self.key())
        if not book_listing:
          book = Book.get(self.book_id)
          book_listing = book.summary_belong()
          book_listing += book.transitions()
          book_listing += line_break
          memcache.set(self.key(), book_listing)
        return book_listing

    def reset(self):
        logging.info("Reset CacheListingForBorrower "+ self.book_id)
        memcache.delete(self.key())

def before_change(book):
    logging.info("Before Changed: book has changed hands: "+ book.summary())
    if book.is_lent():
        CacheBookIdsBorrowed(str(book.borrower.key())).reset()
        
def after_change(book):
    owners_books = CacheBookIdsOwned(str(book.owner.key())).get()
    if not book.key() in owners_books: #was it just created?
        logging.info("After Changed: Newly added book: "+ book.summary())
        CacheBookIdsOwned(str(book.owner.key())).reset()
        if book.is_technical:
           CacheTechBookIdsOwned(str(book.owner.key())).reset()
    else: #just changed hands?
        logging.info("After Changed: book has changed hands: "+ book.summary())
        CacheListingForOwner(str(book.key())).reset()
        CacheListingForBorrower(str(book.key())).reset()
        CacheListingForViewer(str(book.key())).reset()
        if book.is_lent():
          CacheBookIdsBorrowed(str(book.borrower.key())).reset()
        
def before_delete(book):
    if book.is_lent():
       CacheBookIdsBorrowed(str(book.borrower.key())).reset()
    CacheBookIdsOwned(str(book.owner.key())).reset()
    if book.is_technical:
       CacheTechBookIdsOwned(str(book.owner.key())).reset()
    CacheListingForOwner(str(book.key())).reset()
    CacheListingForBorrower(str(book.key())).reset()
    CacheListingForViewer(str(book.key())).reset()

# change to action specific handlers - not book.put    
Book.change_borrower = pre_process(Book.change_borrower, before_change)
Book.put = post_process(Book.put, after_change)
Book.delete = pre_process(Book.delete, before_delete)