from django.utils import simplejson
from google.appengine.ext import webapp
from wtmb import *
from bookcache import *
from google.appengine.api.datastore_errors import Timeout
from google.appengine.api import users
from google.appengine.ext import db
#################################################    
def belongs_to_friend(groups, me):
    for group in me.member_of:
        if group in groups:
            return True
    return False
#################################################

class FullListing(webapp.RequestHandler):

    def __get_owned_listing(self, me):
            my_unlent_book_keys = map(str, Book.unlent_by(me))
            logging.info(str(len(my_unlent_book_keys)) + ' unlent')
            all_my_book_keys = CacheBookIdsOwned.get(me)
            logging.info(str(len(all_my_book_keys)) + ' in all')
            lent_keyset = set(all_my_book_keys) - set(my_unlent_book_keys)
            needed = 25 - len(lent_keyset)
            if needed < 0:
                needed = 0
            lent_keys = list(lent_keyset)
            keys_for_display = my_unlent_book_keys[:needed]
            #hack: putting lent_keys last bcoz javascript reverses it again, where?
            keys_for_display.extend(lent_keys)
            logging.info(str(len(keys_for_display)) + ' to display')
            return self.__books(keys_for_display)

    def get(self, friend_key=None):
        try:
            self.response.headers['content-type'] = "application/json"
            if friend_key:
                return self.__booksOf(friend_key)
            data = {}
            me = AppUser.me()
            data['user'] = me.to_hash()
            data['own_count'] = me.book_count()
            if(data['own_count'] != len(CacheBookIdsOwned.get(me.key()))):
                logging.error("own count mismatch for %s %s in db %s in cache", me.display_name(), data['own_count'], len(CacheBookIdsOwned.get(me.key())))
            data['mybooks'] = self.__get_owned_listing(me.key())
            data['borrowedBooks'] = self.__books_borrowed_by(me.key())
            data['others'] = self.__friends_books()
            self.response.out.write(simplejson.dumps(data))
        except Timeout:
            self.response.clear()
            self.response.set_status(500, "Operation timed out. Appengine might be going through higher than usual latencies. Please retry.")
            self.response.out.write("Operation timed out. Appengine might be going through higher than usual latencies. Please retry.")

    def __books_borrowed_by(self, appUser_key):
        books_owned_ids = CacheBookIdsBorrowed.get(appUser_key)
        return self.__books(books_owned_ids) if books_owned_ids else []

    def __books(self, books_ids):
        book_hashes = map(CachedBook.get, books_ids)
        return book_hashes

    def __friends_books(self):
        return self.__books(GroupBook.get_friends_books(AppUser.me()))

    def __booksOf(self, friend_key_str):
        result = []
        book_keys_str = CacheBookIdsOwned.get(db.Key(friend_key_str))
        for book_key in book_keys_str:
            result.append(CachedBook.get(book_key))
        self.response.out.write(simplejson.dumps(result))
###############################################3
class Search(webapp.RequestHandler):

    def __getBooksFor(self, result_keys):
        books = []
        for bookey in result_keys:
            try:
                books.append(CachedBook.get(bookey))
            except (Exception, AttributeError):
                logging.warning("book not found for " + bookey)
        return books

    def post(self):
      try:
        term = self.request.get('term')
        logging.info("search term is " + term)
        self.response.headers['content-type'] = "application/json"
        result = []
        me = AppUser.me()
        matches = Book.search(term, 1000, keys_only=True)
        if len(matches) > 0:
            book_keys_str = map(lambda b : str(b[0]), matches)
            if self.request.get('whose'):
                result_keys = set(CacheBookIdsOwned.get(me.key())).intersection(set(book_keys_str))
                result = self.__getBooksFor(result_keys)
            else:
                result_keys_minus_mine = set(book_keys_str) - set(CacheBookIdsOwned.get(me.key()))
                result_keys_str = []
                for book_key_str in result_keys_minus_mine:
                    try:
                        if(Book.get(book_key_str).belongs_to_friend(me)):
                            result_keys_str.append(book_key_str)
                    except (Exception, AttributeError), e:
                        logging.warning("book not found for " + book_key_str)
                result = self.__getBooksFor(result_keys_str)
        self.response.out.write(simplejson.dumps(result))
      except Exception, e:
            logging.exception("search failed")
            self.response.clear()
            self.response.set_status(400, str(e))
            self.response.out.write("oops. something wen't wrong. Please try again.")
