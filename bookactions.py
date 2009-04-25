import cgi
import wsgiref.handlers
import os
import logging

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.api import mail
from google.appengine.api import memcache
from xml.dom import minidom
from wtmb import *
###################################################################
WTMB_SENDER = "whotookmybook@gmail.com"
class ImportASINs(webapp.RequestHandler):
    def breakup(self, my_list): 
     sublist_length = 10    # desired length of the "inner" lists
     list_of_lists = []
     for i in xrange(0, len(my_list), sublist_length):
         list_of_lists.append(my_list[i: i+sublist_length])
     return list_of_lists
    
    def post(self):
        if users.get_current_user():
          appuser = AppUser.getAppUserFor(AppUser(), users.get_current_user())
        asins = self.request.get("asins")
        messages = []
        msg = "asins= "+asins
        logging.info(msg)
        messages.append(msg) #replace this with interception of log.info
        asin_lst = asins.split(',')
        msg = str(len(asin_lst))+" ASINs"
        logging.info(msg)
        messages.append(msg)
        chunks = self.breakup(asin_lst)
        try:  
         for chunk in chunks:
            result = urlfetch.fetch('http://webservices.amazon.com/onca/xml?Service=AWSECommerceService&SubscriptionId=1PKXRTEQQV19XXDW3ZG2&&Operation=ItemLookup&IdType=ASIN&ItemId='+','.join(chunk)+'&ResponseGroup=ItemAttributes')
            amz_ns = 'http://webservices.amazon.com/AWSECommerceService/2005-10-05'
            if result.status_code == 200:
                dom = minidom.parseString(result.content)
                items = dom.getElementsByTagNameNS(amz_ns,'Item')
                for item in items:
                    bk_title = item.getElementsByTagNameNS(amz_ns,'Title')[0].firstChild.data
                    bk_author = item.getElementsByTagNameNS(amz_ns,'Author')[0].firstChild.data
                    is_tech = False
                    try:
                      dewey = item.getElementsByTagNameNS(amz_ns,'DeweyDecimalNumber')[0].firstChild.data
                      is_tech = dewey.startswith("004") or  dewey.startswith("005")
                    except:
                      pass 
                    book = Book(title = bk_title, author = bk_author, owner = appuser, is_technical = is_tech)
                    book.put()
                    msg = "added:  "+book.summary()
                    logging.info(msg)
                    messages.append(msg)
            else:
                msg = "amz lookup failed with code "+ result.status_code
                logging.info(msg)
                messages.append(msg)
         self.response.out.write('\n'.join(messages))
        except:
            raise
        
class AddToBookshelf(webapp.RequestHandler):
  def post(self):
    if users.get_current_user():
      appuser = AppUser.getAppUserFor(AppUser(), users.get_current_user())
    book = Book(title = self.request.get('book_title'), author = self.request.get('book_author'), owner = appuser, is_technical = self.dewey_4_or_5(self.request.get('book_asin')))
    book.put()
    self.redirect('/mybooks')
    
  def dewey_4_or_5(self, asin):
    logging.debug("looking up amz for deway")
    try:  
        result = urlfetch.fetch('http://webservices.amazon.com/onca/xml?Service=AWSECommerceService&SubscriptionId=1PKXRTEQQV19XXDW3ZG2&&Operation=ItemLookup&IdType=ASIN&ItemId='+asin+'&ResponseGroup=ItemAttributes')
        amz_ns = 'http://webservices.amazon.com/AWSECommerceService/2005-10-05'
        if result.status_code == 200:
            dom = minidom.parseString(result.content)
            item = dom.getElementsByTagNameNS(amz_ns,'Item')[0]
            dewey = item.getElementsByTagNameNS(amz_ns,'DeweyDecimalNumber')[0].firstChild.data
            logging.debug("dewey is "+ dewey)
            return dewey.startswith("004") or  dewey.startswith("005") 
        else:
            return False;
    except:
        return False;
###################################################################
class Borrow(webapp.RequestHandler):
  def get(self, bookid):
    bookToLoan = Book.get(bookid)
    if bookToLoan.belongs_to_someone_else():
      bookToLoan.change_borrower(AppUser.getAppUserFor(AppUser(), users.get_current_user()))
      bookToLoan.put()
      mail.send_mail(WTMB_SENDER,[users.get_current_user().email(), bookToLoan.owner.email()], '[whotookmybook] '+bookToLoan.title, users.get_current_user().nickname() + "has borrowed this book from " + bookToLoan.owner.display_name())
    self.redirect('/mybooks')
###################################################################    
class DeleteBook(webapp.RequestHandler):
  def get(self, bookid):
    Book.get(bookid).obliterate()
    self.redirect('/mybooks')
###################################################################    
class ReturnBook(webapp.RequestHandler):
  def get(self, bookid):
    rtnd_book = Book.get(bookid)
    if rtnd_book.borrowed_by_me():
      rtnd_book.return_to_owner()
      rtnd_book.put()
      mail.send_mail(WTMB_SENDER, [users.get_current_user().email(), rtnd_book.owner.email()], '[whotookmybook] '+rtnd_book.title, users.get_current_user().nickname()+" has returned this book to "+rtnd_book.owner.display_name())
    self.redirect('/mybooks')
###################################################################    
class LendTo(webapp.RequestHandler):
  def get(self, what_and_who):
    parts = what_and_who.split('/')
    bookid = parts[len(parts) - 2]
    lendTo = parts[len(parts) - 1]
    bookToLoan = Book.get(bookid)
    if bookToLoan.belongs_to_me():
      bookToLoan.change_borrower(AppUser.get(db.Key(lendTo)))
      bookToLoan.put()
      mail.send_mail(WTMB_SENDER, [users.get_current_user().email(), bookToLoan.borrower.email()], '[whotookmybook] '+bookToLoan.title, users.get_current_user().nickname() + " has lent this book to " + bookToLoan.borrower.display_name())
    self.redirect('/mybooks')
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
      'members': AppUser.others(AppUser()),
      'url': url,
      'url_linktext': url_linktext,
      }
    path = os.path.join(os.path.dirname(__file__), 'lend.html')
    self.response.out.write(template.render(path, template_values))
###################################################################    
class Suggest(webapp.RequestHandler):
  def get(self, *args):
    logging.info("looking up amz for: "+ self.request.get('fragment'))  
    result = urlfetch.fetch('http://webservices.amazon.com/onca/xml?Service=AWSECommerceService&SubscriptionId=1PKXRTEQQV19XXDW3ZG2&&Operation=ItemSearch&Keywords='+self.request.get('fragment')+'&SearchIndex=Books&ResponseGroup=Small')
    r = '{ results: ['
    list = []
    amz_ns = 'http://webservices.amazon.com/AWSECommerceService/2005-10-05'
    if result.status_code == 200:
        dom = minidom.parseString(result.content)
        for item in dom.getElementsByTagNameNS(amz_ns,'Item'):
           asin = item.getElementsByTagNameNS(amz_ns,'ASIN')[0].firstChild.data
           node = item.getElementsByTagNameNS(amz_ns,'ItemAttributes')[0]
           title = node.getElementsByTagNameNS(amz_ns,'Title')[0].firstChild.data
           authors = node.getElementsByTagNameNS(amz_ns,'Author')
           author = 'unknown'
           if authors.length > 0 :
             author = authors[0].firstChild.data
           list.append('{ id:"'+  asin +'",value:"'+ cgi.escape(title) +'",info:"' + cgi.escape(author)+'"}')

        r += ','.join(list)
        r += ']}'
        self.response.headers['Content-Type'] = "text/javascript"
        self.response.out.write(r)
###################################################################    
class ShowAll(webapp.RequestHandler):
  def get(self):
    memcache.delete(self.tech_option_key_for(AppUser.getAppUserFor(AppUser(), users.get_current_user())))  
    self.redirect('/mybooks')
#  how to not dup this
  def tech_option_key_for(self, appuser):
        return "tech_option_key_for_" + str(appuser.key())
###################################################################    
class ShowTechOnly(webapp.RequestHandler):
  def get(self):
    memcache.set(self.tech_option_key_for(AppUser.getAppUserFor(AppUser(), users.get_current_user())), "yes")  
    self.redirect('/mybooks')
#  how to not dup this
  def tech_option_key_for(self, appuser):
        return "tech_option_key_for_" + str(appuser.key())
