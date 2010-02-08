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
            lent_keys.extend(my_unlent_book_keys[:needed])
            logging.info(str(len(lent_keys)) + ' to display')
            return self.books_by_title(lent_keys)

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
            data['own_count'] = len(CacheBookIdsOwned.get(me))            
            data['mybooks'] = self.get_owned_listing(me.key())
            data['borrowedBooks'] = self.books_borrowed_by(me.key())
            friends_books = []
            for friend in AppUser.others():
                batch = CacheBookIdsOwned.get(friend.key())
                needed = 25 - len(friends_books)
                friends_books.extend(self.books_by_title(list(batch)[:needed]))
                if len(friends_books) >= 25:
                    break
            data['others'] = friends_books
            self.response.out.write(simplejson.dumps(data))
        except Timeout:
            self.response.clear()
            self.response.set_status(500, "Operation timed out. Appengine might be going through higher than usual latencies. Please retry.")
            self.response.out.write("Operation timed out. Appengine might be going through higher than usual latencies. Please retry.")

    def books_owned_by(self, appUser_key):
        books_owned_ids = CacheBookIdsOwned.get(appUser_key)
        return self.books_by_title(books_owned_ids) if books_owned_ids else []

    def books_borrowed_by(self, appUser_key):
        books_owned_ids = CacheBookIdsBorrowed.get(appUser_key)
        return self.books_by_title(books_owned_ids) if books_owned_ids else []

    def books_by_title(self, books_owned_ids):
        book_hashes = map(CachedBook.get, books_owned_ids)
        book_hashes.sort(lambda x, y: cmp(y['title'], x['title']))
        return book_hashes
###############################################3
class Search(webapp.RequestHandler):
    def post(self):
        term = self.request.get('term')
        self.response.headers['content-type'] = "application/json"
        result = []
        me = AppUser.me()
        matches = Book.search(term, 1000, keys_only=True)
        book_keys = map(lambda b : str(b[0]), matches)
        for mybook_key in CacheBookIdsOwned.get(me.key()):
            try:
                book_keys.remove(mybook_key)
            except ValueError:
                pass
        books = map(CachedBook.get, book_keys)
        for book in books:
            if belongs_to_friend(book["owner_groups"], me):
                result.append(book)
        self.response.out.write( simplejson.dumps(result))