import cgi
import wsgiref.handlers
import os
import logging
import urllib

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.api import mail
from django.utils import simplejson
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

    def get_items_from_result(self, result):
        dom = minidom.parseString(result.content)
        return dom.getElementsByTagNameNS(self.amz_ns, 'Item')

    def get_attribs_for_items(self, asin_csv):
        return urlfetch.fetch(self.amz_url + 'Operation=ItemLookup&IdType=ASIN&ItemId=' + asin_csv + '&ResponseGroup=ItemAttributes')

    def get_books_for_asins(self, asin_lst):
        books = []
        asin_lst = map(lambda asin: unicode.strip(asin).zfill(10), asin_lst)
        result = self.get_attribs_for_items(','.join(asin_lst))
        if result.status_code == 200:
            items = self.get_items_from_result(result)
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
            report("Did you enter comma separated ASINs?\namz lookup failed with code " + str(result.status_code))
        return books

    def get_dewey(self, asin):
        if asin == '0':
            return None
        try:
            result = self.get_attribs_for_items(asin)
            if result.status_code == 200:
                item = self.get_items_from_result(result)[0]
                return self.__dewey_decimal_of(item)
        except:
            logging.error("exception in dewey lookup")
            return None

    def search_by(self, searchString):
        result = urlfetch.fetch(self.amz_url + 'Operation=ItemSearch&Keywords=' + searchString + '&SearchIndex=Books&ResponseGroup=Small')
        list = []
        if result.status_code == 200:
            for item in self.get_items_from_result(result):
               asin = self.__asin_of(item)
               node = item.getElementsByTagNameNS(self.amz_ns, 'ItemAttributes')[0]
               title = self.__title_of(node)
               author = self.__author_of(node)
               if not author:
                   author = 'unknown'
               list.append(simplejson.dumps({ "id" : asin , "value" : title , "info" : author}))
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
                self.response.set_status(412, "You already have this book. Cannot add again.")
            except BookWithoutTitle:
                self.response.set_status(412, "Title required")
        else:
            self.error(401) #need to include www-auth??

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
                     body = users.get_current_user().nickname() + " has requested or borrowed this book from " + bookToLoan.owner.display_name())
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
        old_borrower = rtnd_book.borrower
        if old_borrower:
            rtnd_book.return_to_owner()
            mail.send_mail(
                         sender = WTMB_SENDER,
                         to = [old_borrower.email(), rtnd_book.owner.email()],
                         cc = WTMB_SENDER,
                         subject = '[whotookmybook] ' + rtnd_book.title,
                         body = (AppUser.me().display_name() + \
                                 (" has returned this book to " + rtnd_book.owner.display_name()) if (AppUser.me() != rtnd_book.owner) else \
                                 AppUser.me().display_name() + " has asserted possession of this book"))

        else:
            logging.warning(users.get_current_user().email() + " attempted to return book that wasn't borrowed " + rtnd_book.summary())
        self.redirect('/mybooks')
    except IllegalStateTransition:
        self.error(403)

###################################################################    
class LendTo(webapp.RequestHandler):
  def post(self):
    bookid = self.request.get('book_id')
    lendTo = self.request.get('lend_to')
    new_user_name = self.request.get('new_user')
    if (lendTo and new_user_name) or (not lendTo and not new_user_name):
        self.response.set_status(400, 'Please send exactly one of lendTo and new_user')
        return
    try:
        bookToLoan = Book.get(bookid)
        borrower = None
        if lendTo:
            borrower = AppUser.get(db.Key(lendTo))
        else:
            borrower = AppUser.create_outsider(new_user_name)
        bookToLoan.lend_to(borrower)
        mail.send_mail(
                     sender = WTMB_SENDER,
                     to = [users.get_current_user().email(), bookToLoan.borrower.email()],
                     cc = WTMB_SENDER,
                     subject = '[whotookmybook] ' + bookToLoan.title,
                     body = users.get_current_user().nickname() + " has lent this book to " + bookToLoan.borrower.display_name())
    except IllegalStateTransition:
        self.response.set_status(403, 'Illegal State Transition')
    except ValueError, v:
        self.response.set_status(400, str(v))

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
class Nickname(webapp.RequestHandler):
    def post(self):
        new_nick = self.request.get('new_nick')
        if not new_nick or new_nick.strip() == "":
            self.response.set_status(400, "Empty Nickname")
            return
        me = AppUser.me()
        me.change_nickname(cgi.escape(new_nick))
