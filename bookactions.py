import cgi
import wsgiref.handlers
import os
import logging
import urllib

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.api import mail
from xml.dom import minidom
from wtmb import *

###################################################################
WTMB_SENDER = "whotookmybook@gmail.com"
WTMB_LINK = '\nGo to <a href="http://whotookmybook.appspot.com/mybooks">who took my book</a>'
messages = []

def report(msg):
    logging.info(msg)
    messages.append(msg)
###################################################################
class Amz:

    def __init__(self):
        self.amz_ns = 'http://webservices.amazon.com/AWSECommerceService/2005-10-05'
        self.amz_url = 'http://webservices.amazon.com/onca/xml?Service=AWSECommerceService&SubscriptionId=1PKXRTEQQV19XXDW3ZG2&'

    def __asin_of(self, item):
        return item.getElementsByTagNameNS(self.amz_ns, 'ASIN')[0].firstChild.data


    def __is_tech_dewey(self, dewey):
        return dewey.startswith("004") or dewey.startswith("005")


    def __dewey_decimal_of(self, node):
        return node.getElementsByTagNameNS(self.amz_ns, 'DeweyDecimalNumber')[0].firstChild.data

    def __author_of(self, node):
        try:
            return node.getElementsByTagNameNS(self.amz_ns, 'Author')[0].firstChild.data
        except:
            return None

    def __title_of(self, node):
        return node.getElementsByTagNameNS(self.amz_ns, 'Title')[0].firstChild.data

    def get_items_from_result(self, result):
        dom = minidom.parseString(result.content)
        return dom.getElementsByTagNameNS(self.amz_ns, 'Item')

    def get_attribs_for_items(self, asin_csv):
        return urlfetch.fetch(self.amz_url + 'Operation=ItemLookup&IdType=ASIN&ItemId=' + asin_csv + '&ResponseGroup=ItemAttributes')

    def get_books_for_asins(self, asin_lst):
        books = []
        asin_lst = map(unicode.strip, asin_lst)
        result = self.get_attribs_for_items(','.join(asin_lst))
        if result.status_code == 200:
            items = self.get_items_from_result(result)
            for item in items:
                bk_title = self.__title_of(item)
                bk_author = self.__author_of(item)
                is_tech = False
                try:
                  dewey = self.__dewey_decimal_of(item)
                  is_tech = self.__is_tech_dewey(dewey)
                except:
                  pass
                book = Book(title = bk_title, author = bk_author, is_technical = is_tech)
                books.append(book)
        else:
            report("Did you enter comma separated ASINs?\namz lookup failed with code " + str(result.status_code))
        return books

    def lookup_if_technical(self, asin):
        logging.info("deway lookup")
        try:
            result = self.get_attribs_for_items(asin)
            if result.status_code == 200:
                item = self.get_items_from_result(result)[0]
                dewey = self.__dewey_decimal_of(item)
                logging.info("dewey is " + dewey)
                return self.__is_tech_dewey(dewey)
            else:
                return False;
        except:
            logging.error("exception in dewey lookup")
            return False;

    def search_by(self, searchString):
        result = urlfetch.fetch(self.amz_url + 'Operation=ItemSearch&Keywords=' + urllib.quote(searchString) + '&SearchIndex=Books&ResponseGroup=Small')
        list = []
        if result.status_code == 200:
            for item in self.get_items_from_result(result):
               asin = self.__asin_of(item)
               node = item.getElementsByTagNameNS(self.amz_ns, 'ItemAttributes')[0]
               title = self.__title_of(node)
               author = self.__author_of(node)
               if not author:
                   author = 'unknown'
               list.append('{ id:"' + asin + '",value:"' + cgi.escape(title) + '",info:"' + cgi.escape(author) + '"}')
        return list
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
                   book.owner = appuser
                   book.create()
                   report("added:  " + book.summary())
            self.response.headers['Content-Type'] = "text/plain"
            self.response.out.write('\n'.join(messages))
            del messages[:]
        except:
            raise
###################################################################
class AddToBookshelf(webapp.RequestHandler):
  def post(self):
    try:
        if users.get_current_user():
            appuser = AppUser.getAppUserFor(users.get_current_user())
            book = Book(
                            title = self.request.get('book_title'),
                            author = self.request.get('book_author'),
                            owner = appuser,
                            is_technical = Amz().lookup_if_technical(self.request.get('book_asin')))
            book.create() # doesn't work if create is chained to constr above!
            self.response.headers['content-type'] = "application/json"
            self.response.out.write(book.to_json())
        else:
            self.error(401) #need to include www-auth??
    except:
        raise

###################################################################
class Borrow(webapp.RequestHandler):
    def get(self, bookid):
        bookToLoan = Book.get(bookid)
        try:
            bookToLoan.borrow()
            mail.send_mail(
                     sender = WTMB_SENDER,
                     to = [users.get_current_user().email(), bookToLoan.owner.email()],
                     cc = WTMB_SENDER,
                     subject = '[whotookmybook] ' + bookToLoan.title,
                     body = users.get_current_user().nickname() + " has borrowed this book from " + bookToLoan.owner.display_name())
            self.redirect('/mybooks')
        except IllegalStateTransition:
            self.error(403)

###################################################################    
class DeleteBook(webapp.RequestHandler):
  def get(self, bookid):
    try:
        Book.get(bookid).obliterate()
        self.redirect('/mybooks')
    except IllegalStateTransition:
        self.error(403)

###################################################################    
class ReturnBook(webapp.RequestHandler):
  def get(self, bookid):
    rtnd_book = Book.get(bookid)
    try:
        rtnd_book.return_to_owner()
        mail.send_mail(
                     sender = WTMB_SENDER,
                     to = [users.get_current_user().email(), rtnd_book.owner.email()],
                     cc = WTMB_SENDER,
                     subject = '[whotookmybook] ' + rtnd_book.title,
                     body = users.get_current_user().nickname() + " has returned this book to " + rtnd_book.owner.display_name())
        self.redirect('/mybooks')
    except IllegalStateTransition:
        self.error(403)

###################################################################    
class LendTo(webapp.RequestHandler):
  def get(self, what_and_who):
    parts = what_and_who.split('/')
    bookid = parts[len(parts) - 2]
    lendTo = parts[len(parts) - 1]
    bookToLoan = Book.get(bookid)
    try:
        bookToLoan.lend_to(AppUser.get(db.Key(lendTo)))
        mail.send_mail(
                     sender = WTMB_SENDER,
                     to = [users.get_current_user().email(), bookToLoan.borrower.email()],
                     cc = WTMB_SENDER,
                     subject = '[whotookmybook] ' + bookToLoan.title,
                     body = users.get_current_user().nickname() + " has lent this book to " + bookToLoan.borrower.display_name())
        self.redirect('/mybooks')
    except IllegalStateTransition:
        self.error(403)

###################################################################    
class Lend(webapp.RequestHandler):
  def get(self, what):
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url(self.request.uri))
    if users.get_current_user():
      url = users.create_logout_url("/mybooks")
      url_linktext = 'Logout'
    else:
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'
    template_values = {
      'book': Book.get(db.Key(what)),
      'members': AppUser.others(),
      'url': url,
      'url_linktext': url_linktext,
      }
    path = os.path.join(os.path.dirname(__file__), 'lend.html')
    self.response.out.write(template.render(path, template_values))

###################################################################    
class Suggest(webapp.RequestHandler):
  def get(self, *args):
    logging.info("looking up amz for: " + self.request.get('fragment'))
    r = '{ results: ['
    list = Amz().search_by(self.request.get('fragment'))
    r += ','.join(list)
    r += ']}'
    self.response.headers['Content-Type'] = "application/json"
    self.response.out.write(r)
###################################################################
