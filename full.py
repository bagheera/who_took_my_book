from django.utils import simplejson
from google.appengine.ext import webapp
from wtmb import *
from bookcache import *
from google.appengine.api.datastore_errors import Timeout
from google.appengine.api import users

class FullListing(webapp.RequestHandler):

    def get(self):
        #workaround for cron: X-AppEngine-Cron: true
        if not users.get_current_user() and not self.request.headers.get('X-AppEngine-Cron', None):
            logging.warning('attempted access by other than X-AppEngine-Cron');
            self.response.set_status(401)
            return
        try:
            self.response.headers['content-type'] = "application/json"
            data = {}
            me = AppUser.me()
            data['user'] = me.to_hash()
            data['mybooks'] = self.books_owned_by(me)
            data['borrowedBooks'] = self.books_borrowed_by(AppUser.me())
#          Having to do manual filtering coz 'Keys only queries do not support IN or != filters.'
            others_books = []
            all_book_keys = Book.all_books()
            logging.info("all books count " + str(len(all_book_keys)))
            my_book_keys = Book.owned_by(AppUser.me().key())
            for my_book_key in my_book_keys:
                try:
                    all_book_keys.remove(my_book_key)
                except ValueError:
                    logging.error("not found "+ str(my_book_key))
            others_books = map(CachedBook.get, map(str, all_book_keys))
            data['others'] = others_books
            self.response.out.write(simplejson.dumps(data))
        except Timeout:
            self.response.clear()
            self.response.set_status(500, "Operation timed out. Appengine might be going through higher than usual latencies. Please retry.")
            self.response.out.write("Operation timed out. Appengine might be going through higher than usual latencies. Please retry.")

    def books_owned_by(self, appUser_key):
        books_owned_ids = CacheBookIdsOwned.get(appUser_key)
        return self.books_by_title(books_owned_ids) if books_owned_ids else []

    def books_borrowed_by(self, appUser):
        books_owned_ids = CacheBookIdsBorrowed.get(appUser.key())
        return self.books_by_title(books_owned_ids) if books_owned_ids else []

    def books_by_title(self, books_owned):
        book_hashes = map(CachedBook.get, books_owned)
        book_hashes.sort(lambda x, y: cmp(y['title'], x['title']))
        return book_hashes

