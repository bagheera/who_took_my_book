from django.core import validators
from django.utils import simplejson
from google.appengine.ext import webapp
from wtmb import *
from amz import Amz
from bookcache import CachedBook

###################################################################
def cache_for(response, ndays, nhours=0):
      response.headers['Cache-Control'] = 'public, max-age=%d' % (86400 * ndays + (3600 * nhours),)
      lastmod = datetime.utcnow()
      response.headers['Last-Modified'] = lastmod.strftime('%a, %d %b %Y %H:%M:%S GMT')
      expires = lastmod + timedelta(days=ndays, hours=nhours)
      response.headers['Expires'] = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
###################################################################
messages = []

def report(msg):
    logging.info(msg)
    messages.append(msg)

class ImportASINs(webapp.RequestHandler):

    def breakup(self, my_list):
     sublist_length = 10    # desired length of the "inner" lists
     list_of_lists = []
     for i in xrange(0, len(my_list), sublist_length):
         list_of_lists.append(my_list[i: i + sublist_length])
     return list_of_lists

    def post(self):
        asins = self.request.get("asins")
        report("asins= %s" % asins)
        asin_lst = asins.split(',')
        report("ASINs %s" % (len(asin_lst)))
        try:
            chunks = self.breakup(asin_lst)
            for chunk in chunks:
               # can the fetch and persist be parallelised like in scala?
               books = Amz().get_books_for_asins(chunk)
               if len(books) == 0:
                   report("Amazon returned no results for these ASINs")
               for book in books:
                   try:
                       book.owner = AppUser.me()
                       book.create()
                       report("added: %s" % book.summary())
                   except DuplicateBook:
                        report("duplicate book: %s" % book.summary())
                   except:
                        report("could not add: %s" % book.summary())
            self.response.headers['Content-Type'] = "text/plain"
            self.response.out.write('\n'.join(messages))
            #todo :add a back button 
            del messages[:]
        except:
            raise
###################################################################
class AddToBookshelf(webapp.RequestHandler):
  def post(self):
        if users.get_current_user():
            appuser = AppUser.me()
            book_asin = self.request.get('book_asin')
            try:
                dewey_num = Amz().get_dewey(book_asin)
                book = Book(
                            title=self.request.get('book_title'),
                            author=self.request.get('book_author'),
                            owner=appuser,
                            asin=book_asin,
                            dewey=dewey_num,
                            is_technical=Amz().is_tech_dewey(dewey_num))
                book.create()
                self.response.headers['content-type'] = "application/json"
                self.response.out.write(simplejson.dumps(book.to_hash()))
#                how to say as dupbook?
            except DuplicateBook:
                self.response.clear()
                self.response.set_status(412)
                self.response.out.write("This book is already present in your list")
            except BookWithoutTitle:
                self.response.clear()
                self.response.set_status(412)
                self.response.out.write("Title Required")
        else:
            self.error(401) #need to include www-auth??

###################################################################
class Borrow(webapp.RequestHandler):
    def post(self, bookid):
        bookToLoan = Book.get(bookid)
        try:
            bookToLoan.borrow()
            self.response.headers['content-type'] = "application/json"
            self.response.out.write(simplejson.dumps(CachedBook.get(bookid)))
        except IllegalStateTransition:
            self.error(403)

###################################################################    
class DeleteBook(webapp.RequestHandler):
  def get(self, bookid):
    try:
        doomedBook = Book.get(bookid)
        if doomedBook:
            doomedBook.obliterate()
        else:
            logging.warning("Cant find book to be deleted: %s" % bookid)
        self.redirect('/mybooks')
    except IllegalStateTransition:
        self.error(403)

###################################################################    
class ReturnBook(webapp.RequestHandler):
  def post(self, bookid):
    rtnd_book = Book.get(bookid)
    try:
        if rtnd_book.borrower: #move this check to book
            rtnd_book.return_to_owner()
        else:
            logging.warning("%s attempted to return book that wasn't borrowed %s" % (users.get_current_user().email(), rtnd_book.summary()))
        self.response.headers['content-type'] = "application/json"
        self.response.out.write(simplejson.dumps(CachedBook.get(bookid)))
    except IllegalStateTransition:
        self.error(403)

###################################################################    
class LendTo(webapp.RequestHandler):

  def error_response(self, status_code, message):
      self.response.clear()
      self.response.set_status(status_code, message)
      self.response.out.write(message)

  def post(self):
    bookid = self.request.get('book_id')
    lendTo = self.request.get('lend_to')
    new_user_name = self.request.get('new_user')
    new_user_email = self.request.get('new_user_email')
    if not (lendTo or new_user_name):
        self.response.clear()
        self.response.set_status(400)
        self.response.out.write("oops. something wen't wrong. Please try again.")
        return
    try:
        bookToLoan = Book.get(bookid)
        borrower = None
        if lendTo:
            borrower = AppUser.get(db.Key(lendTo))
        else:
            if new_user_name.strip() == '':
                self.error_response(400, "Name is empty")
                return
            if new_user_email and not validators.email_re.search(new_user_email):
                self.error_response(400, "Invalid email")
                return
            borrower = AppUser.create_outsider(new_user_name, bookToLoan, new_user_email)
        bookToLoan.lend_to(borrower)
    except IllegalStateTransition:
        self.error_response(403, 'Illegal State Transition')
    except ValueError, v:
        self.error_response(400, str(v))

###################################################################    
class Suggest(webapp.RequestHandler):
  def get(self, *args):
    logging.info("looking up amz for: %s" % self.request.get('fragment'))
    r = '{ results: ['
    list = Amz().search_by(self.request.get('fragment'))
    r += ','.join(list)
    r += ']}'
    self.response.headers['Content-Type'] = "application/json"
    cache_for(self.response, 1)
    self.response.out.write(r)
###################################################################
class Nickname(webapp.RequestHandler):
    def post(self):
        new_nick = self.request.get('new_nick')
        if not new_nick or new_nick.strip() == "":
            self.response.clear()
            self.response.set_status(400, "Empty Nickname")
            self.response.out.write("Empty Nickname")
            return
        me = AppUser.me()
        me.change_nickname(new_nick)
###################################################################
class Remind(webapp.RequestHandler):
    def post(self):
        try:
            book_id = self.request.get('book_id')
            Book.get(book_id).remind()
        except Exception, e:
            logging.exception("remind failed")
            self.response.clear()
            self.response.set_status(400, str(e))
            self.response.out.write("oops. something wen't wrong. Please try again.")
###################################################################
class LookupUzer(webapp.RequestHandler):
    def get(self, *args):
        fragment = self.request.get('fragment')
        matches = []
        for user in AppUser.friends():
            if user.matches(fragment):
                matches.append(user)
                if len(matches) > 6:
                    break
        suggestions = map(lambda user : {"id" : str(user.key()),
                                         "value" : user.display_name(),
                                         "info" : user.email()}, matches)
        self.response.out.write(simplejson.dumps({"results" : suggestions}))
###################################################################        
class IndexBook(webapp.RequestHandler):
    def post(self):
        batch = self.request.get('keycsv').split(',')
        logging.debug("IndexBook batch is: %d" % (batch,))
        for book in Book.get(batch):
            book.index()
###################################################################        
class PurgeInactiveUsers(webapp.RequestHandler):
    def post(self):
        batch = self.request.get('keycsv').split(',')
        logging.info("PurgeInactiveUsers batch is: %d" % (batch,))
        for user in AppUser.get(batch):
            user.purge()
###################################################################        
class MakeGroupBooks(webapp.RequestHandler):
    def post(self):
        batch = self.request.get('groupbooks').split('|')
        for groupBookStr in batch:
            parts = groupBookStr.split(',')
            GroupBook(owner=AppUser.get(parts[0]),
                      group=Group.get(parts[1]),
                      book=Book.get(parts[2]),
                      added_on=Book.get(parts[2]).created_date).put()
