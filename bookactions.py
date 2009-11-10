from django.core import validators
from django.utils import simplejson
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from wtmb import *
from xml.dom import minidom
import cgi
import logging
import os
import re
import urllib
import wsgiref.handlers
from datetime import datetime, timedelta


###################################################################
messages = []

def report(msg):
    logging.info(msg)
    messages.append(msg)
###################################################################
def cache_for(response, ndays, nhours=0):
      response.headers['Cache-Control']='public, max-age=' + str(86400 * ndays + (3600 * nhours))
      lastmod = datetime.utcnow()
      response.headers['Last-Modified'] = lastmod.strftime('%a, %d %b %Y %H:%M:%S GMT')
      expires=lastmod+timedelta(days=ndays, hours=nhours)
      response.headers['Expires'] = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
###################################################################

class Amz:

    def __init__(self):
        self.amz_ns = 'http://webservices.amazon.com/AWSECommerceService/2008-08-19'

    def __asin_of(self, item):
        return item.getElementsByTagNameNS(self.amz_ns, 'ASIN')[0].firstChild.data


    def is_tech_dewey(self, dewey):
        return bool(dewey) and (dewey.startswith("004") or dewey.startswith("005"))


    def __dewey_decimal_of(self, node):
        dd = node.getElementsByTagNameNS(self.amz_ns, 'DeweyDecimalNumber')
        return dd[0].firstChild.data if len(dd) > 0 else None

    def __author_of(self, node):
        try:
            return node.getElementsByTagNameNS(self.amz_ns, 'Author')[0].firstChild.data
        except:
            return None

    def __title_of(self, node):
        return node.getElementsByTagNameNS(self.amz_ns, 'Title')[0].firstChild.data

    def __asin_of(self, node):
        return node.getElementsByTagNameNS(self.amz_ns, 'ASIN')[0].firstChild.data

    def get_items_from_result(self, responseBodyText):
        dom = minidom.parseString(responseBodyText)
        return dom.getElementsByTagNameNS(self.amz_ns, 'Item')

    def get_attribs_for_items(self, asin_csv):
        return self.amz_call({'Operation' : 'ItemLookup' , 'IdType' : 'ASIN' , 'ItemId' : asin_csv , 'ResponseGroup' : 'ItemAttributes' })

    def get_books_for_asins(self, asin_lst):
        books = []
        asin_lst = map(lambda asin: unicode.strip(asin).zfill(10), asin_lst)
        result = self.get_attribs_for_items(','.join(asin_lst))
        if result.status == 200:
            items = self.get_items_from_result(result.read())
            for item in items:
                try:
                    bk_title = self.__title_of(item)
                    bk_author = self.__author_of(item)
                    bk_asin = self.__asin_of(item)
                    is_tech = False
                    dewey_decimal = self.__dewey_decimal_of(item)
                    is_tech = self.is_tech_dewey(dewey_decimal)
                    book = Book(title = bk_title, author = bk_author, is_technical = is_tech, asin = bk_asin, dewey = dewey_decimal)
                    books.append(book)
                except:
                  pass
        else:
            report("Did you enter comma separated ASINs?\namz lookup failed with code " + str(result.status))
        return books

    def get_dewey(self, asin):
        if asin == '0':
            return None
        try:
            result = self.get_attribs_for_items(asin)
            if result.status == 200:
                item = self.get_items_from_result(result.read())[0]
                return self.__dewey_decimal_of(item)
        except:
            logging.error("exception in dewey lookup")
            return None

    def search_by(self, searchString):
        result = self.amz_call({'Operation' : 'ItemSearch' , 'Keywords' : urllib.unquote(searchString) , 'SearchIndex' : 'Books' , 'ResponseGroup' : 'Small' })
        list = []
        if result.status == 200:
            responseBodyText = result.read(result.fp.len)
            for item in self.get_items_from_result(responseBodyText):
               asin = self.__asin_of(item)
               node = item.getElementsByTagNameNS(self.amz_ns, 'ItemAttributes')[0]
               title = self.__title_of(node)
               author = self.__author_of(node)
               if not author:
                   author = 'unknown'
               list.append(simplejson.dumps({ "id" : asin , "value" : title , "info" : author}))
        return list
    
    keyFile = open('accesskey.secret', 'r')
    AWS_SECRET_ACCESS_KEY = keyFile.read()
    keyFile.close()
    def amz_call(self, call_params):
        
        AWS_ACCESS_KEY_ID = '1PKXRTEQQV19XXDW3ZG2'
        AWS_ASSOCIATE_TAG = 'whotookmybook-20'
                
        import time
        import urllib
        from boto.connection import AWSQueryConnection
        aws_conn = AWSQueryConnection(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Amz.AWS_SECRET_ACCESS_KEY, is_secure=False,
            host='ecs.amazonaws.com')
        aws_conn.SignatureVersion = '2'
        base_params = dict(
            Service='AWSECommerceService',
            Version='2008-08-19',
            SignatureVersion=aws_conn.SignatureVersion,
            AWSAccessKeyId=AWS_ACCESS_KEY_ID,
            AssociateTag=AWS_ASSOCIATE_TAG,
            Timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()))
        params = dict(base_params, **call_params) #http://stackoverflow.com/questions/38987/how-can-i-merge-two-python-dictionaries-as-a-single-expression
        verb = 'GET'
        path = '/onca/xml'
        qs, signature = aws_conn.get_signature(params, verb, path)
        qs = path + '?' + qs + '&Signature=' + urllib.quote(signature)
        return aws_conn._mexe(verb, qs, None, headers={})
###################################################################
class ImportASINs(webapp.RequestHandler):
    def breakup(self, my_list):
     sublist_length = 10    # desired length of the "inner" lists
     list_of_lists = []
     for i in xrange(0, len(my_list), sublist_length):
         list_of_lists.append(my_list[i: i + sublist_length])
     return list_of_lists

    def post(self):
        if users.get_current_user():
            appuser = AppUser.getAppUserFor(users.get_current_user())
        asins = self.request.get("asins")
        report("asins= " + asins)
        asin_lst = asins.split(',')
        report(str(len(asin_lst)) + " ASINs")
        try:
            chunks = self.breakup(asin_lst)
            for chunk in chunks:
               # can the fetch and persist be parallelised like in scala?
               books = Amz().get_books_for_asins(chunk)
               if len(books) == 0:
                   report("Amazon returned no results for these ASINs")
               for book in books:
                   try:
                       book.owner = appuser
                       book.create()
                       report("added:  " + book.summary())
                   except DuplicateBook:
                        report("duplicate book: " + book.summary())
                   except:
                        report("could not add: " + book.summary())
            self.response.headers['Content-Type'] = "text/plain"
            self.response.out.write('\n'.join(messages))
            del messages[:]
        except:
            raise
###################################################################
class AddToBookshelf(webapp.RequestHandler):
  def post(self):
        if users.get_current_user():
            appuser = AppUser.getAppUserFor(users.get_current_user())
            book_asin = self.request.get('book_asin')
            try:
                dewey_num = Amz().get_dewey(book_asin)
                book = Book(
                            title = self.request.get('book_title'),
                            author = self.request.get('book_author'),
                            owner = appuser,
                            asin = book_asin,
                            dewey = dewey_num,
                            is_technical = Amz().is_tech_dewey(dewey_num))
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
    def get(self, bookid):
        bookToLoan = Book.get(bookid)
        try:
            bookToLoan.borrow()
            self.redirect('/mybooks')
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
            logging.warning("Cant find book to be deleted id " + bookid)
        self.redirect('/mybooks')
    except IllegalStateTransition:
        self.error(403)

###################################################################    
class ReturnBook(webapp.RequestHandler):
  def get(self, bookid):
    rtnd_book = Book.get(bookid)
    try:
        if rtnd_book.borrower: #move this check to book
            rtnd_book.return_to_owner()
        else:
            logging.warning(users.get_current_user().email() + " attempted to return book that wasn't borrowed " + rtnd_book.summary())
        self.redirect('/mybooks')
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
            from google.appengine.api import mail
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
    logging.info("looking up amz for: " + self.request.get('fragment'))
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
            self.response.clear()
            self.response.set_status(400, str(e))
            self.response.out.write("oops. something wen't wrong. Please try again.")
###################################################################
class AllUzers(webapp.RequestHandler):
    def get(self, *args):
        fragment = self.request.get('fragment')
        matches = []
        for user in AppUser.others():
            if user.matches(fragment):
                matches.append(user)
                if len(matches) > 6:
                    break
        suggestions = map(lambda user : {"id" : str(user.key()), "value" : user.display_name(), "info" : user.email()}, matches)
        self.response.out.write(simplejson.dumps({"results" : suggestions}))