from django.utils import simplejson
from google.appengine.ext import webapp
from wtmb import *
from bookcache import *
from google.appengine.api.datastore_errors import Timeout
from google.appengine.api import users
#################################################    
def belongs_to_friend(groups, me):
    for group in me.member_of:
        if group in groups:
            return True
    return False
#################################################

class FullListing(webapp.RequestHandler):

    def get_owned_listing(self, me):
            my_unlent_book_keys = map(str, Book.unlent_by(me))
            logging.info(str(len(my_unlent_book_keys)) + ' unlent')
            all_my_book_keys =  CacheBookIdsOwned.get(me)
            logging.info(str(len(all_my_book_keys)) + ' in all')
            lent_keyset = set(all_my_book_keys) - set(my_unlent_book_keys)
            needed = 25 - len(lent_keyset)
            if needed < 0:
                needed = 0
            lent_keys = list(lent_keyset)
            keys_for_display = my_unlent_book_keys[:needed]
            keys_for_display.extend(lent_keys) #hack: putting lent_keys last bcoz javascript reverses it again
            logging.info(str(len(keys_for_display)) + ' to display')
            return self.books(keys_for_display)

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
            data['own_count'] = me.book_count()
            if(data['own_count'] != len(CacheBookIdsOwned.get(me.key()))):
                logging.error("own count mismatch for %s %s in db %s in cache", me.display_name(), data['own_count'], len(CacheBookIdsOwned.get(me.key())))            
            data['mybooks'] = self.get_owned_listing(me.key())
            data['borrowedBooks'] = self.books_borrowed_by(me.key())
            data['others'] = self.friends_books()
            self.response.out.write(simplejson.dumps(data))
        except Timeout:
            self.response.clear()
            self.response.set_status(500, "Operation timed out. Appengine might be going through higher than usual latencies. Please retry.")
            self.response.out.write("Operation timed out. Appengine might be going through higher than usual latencies. Please retry.")

    def books_owned_by(self, appUser_key):
        books_owned_ids = CacheBookIdsOwned.get(appUser_key)
        return self.books(books_owned_ids) if books_owned_ids else []

    def books_borrowed_by(self, appUser_key):
        books_owned_ids = CacheBookIdsBorrowed.get(appUser_key)
        return self.books(books_owned_ids) if books_owned_ids else []

    def books(self, books_ids):
        book_hashes = map(CachedBook.get, books_ids)
        return book_hashes
    
    def friends_books(self):
        return self.books(GroupBook.get_friends_books(AppUser.me()))
###############################################3
class Search(webapp.RequestHandler):

    def getBooksFor(self, result_keys):
        books = []
        for bookey in result_keys:
            try:
                books.append(CachedBook.get(bookey))
            except (Exception, AttributeError), e:
                logging.warning("book not found for " + bookey)
        return books

    def post(self):
      try:
        term = self.request.get('term')
        logging.info("search term is "+ term)          
        self.response.headers['content-type'] = "application/json"
        result = []
        me = AppUser.me()
        matches = Book.search(term, 1000, keys_only=True)
        if len(matches) > 0:
            book_keys = map(lambda b : str(b[0]), matches)
            if self.request.get('whose'):
                result_keys = set(CacheBookIdsOwned.get(me.key())).intersection(set(book_keys))
                result = self.getBooksFor(result_keys)
            else:
                result_keys = set(book_keys) - set(CacheBookIdsOwned.get(me.key()))
                friends_book_keys = GroupBook.get_friends_book_keys_str(me)
                result = self.getBooksFor(result_keys.intersection(friends_book_keys))
        self.response.out.write( simplejson.dumps(result))
      except Exception, e:
            logging.exception("search failed")
            self.response.clear()
            self.response.set_status(400, str(e))
            self.response.out.write("oops. something wen't wrong. Please try again.")