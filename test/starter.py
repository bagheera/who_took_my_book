import unittest
import logging
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import memcache

from wtmb import *
from mybooks import BookListing
from pymock import *

class BookListTest(PyMockTestCase):

#    def setUp(self):
#        logging.info('In setUp()')
#        
#    def tearDown(self):
#        logging.info('In tearDown()')
#        logging.info(str(memcache.get_stats()))

    def test_should_delete_book_from_cache_when_book_obliterated(self):
        logging.debug("start test")
        memcache.flush_all()
        user = AppUser(googleUser=users.User(email="abc@abc.com"))
        user.put()
        self.override(users, 'get_current_user')
        self.expectAndReturn(users.get_current_user(), user.googleUser)
        self.oneOrMore()
        self.replay()
        book = Book(title="py", author="gos", owner=user)
        book.put()
        self.assertEqual(user, book.owner)
        self.assertFalse(memcache.get(BookListing().bo_listing_key(user)))
        BookListing().books_owned_by(user)
        self.assertTrue(memcache.get(BookListing().bo_listing_key(user)))
        book.obliterate()
        self.assertFalse(memcache.get(BookListing().bo_listing_key(user)))
        user.delete()
        self.verify()

    def test_should_refresh_cache_when_book_returned(self):
        logging.debug("start test")
        memcache.flush_all()
        book_owner = AppUser(googleUser=users.User(email="abc@abc.com"))
        book_owner.put()
        borrower = AppUser(googleUser=users.User(email="xyz@xyz.com"))
        borrower.put()
        book = Book(title="py", author="gos", owner=book_owner)
        book.put()
        book.change_borrower(borrower)
        book.put()
        self.assertFalse(memcache.get(BookListing().bb_listing_key(borrower)))
        BookListing().books_borrowed_by(borrower)
        self.assertTrue(memcache.get(BookListing().bb_listing_key(borrower)))
        self.assertFalse(memcache.get(BookListing().bb_listing_key(book_owner)))
        book.return_to_owner()
        logging.info("about to put after return to owner")
        book.put()
        logging.info("done put after return to owner")
        self.assertFalse(memcache.get(BookListing().bb_listing_key(borrower)))
        book.delete()
        borrower.delete()
        book_owner.delete()
        