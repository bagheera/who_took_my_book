from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import mail

import logging
###################################################################
WTMB_SENDER = "whotookmybook@gmail.com"  
class AppUser(db.Model):
  googleUser = db.UserProperty()
  wtmb_nickname = db.StringProperty()

  def getAppUserFor(self, aGoogleUser):
    appuser = AppUser.gql('WHERE googleUser = :1', aGoogleUser).get()
    if appuser is None:
        appuser = AppUser(googleUser=users.get_current_user())
        appuser.put()
        #bad place for mail
        mail.send_mail(WTMB_SENDER, users.get_current_user().email(), '[whotookmybook] Welcome', "Thanks for choosing to use http://whotookmybook.appspot.com")
    return appuser
    
  def display_name(self):
    return self.googleUser.nickname()
  def email(self):
    return self.googleUser.email()
  def current_AppUser(self):
    return AppUser.gql('WHERE googleUser = :1', users.get_current_user()).get() 
  def others(self):
    return AppUser.gql('WHERE googleUser != :1', users.get_current_user())
###################################################################    
class Book(db.Model):
  author = db.StringProperty()
  owner = db.ReferenceProperty(AppUser, collection_name="books_owned")
  title = db.StringProperty()
  borrower = db.ReferenceProperty(AppUser, collection_name="books_borrowed", required=False)
  uniq = db.StringProperty()
  is_technical = db.BooleanProperty()
  
  def __init__(self, parent=None, key_name=None, **kw):
    super(Book, self).__init__(parent, key_name, **kw)
    if not self.uniq:
      uniq_separator = "_#.,^_"
      self.uniq = self.title + uniq_separator + self.author
    
  def summary(self):
    return self.title + ' by ' + self.author
  
  def summary_belong(self):
    return self.summary() + ' (from ' + self.owner.display_name() + ')'
    
  def summary_loan(self):
    if not self.borrower:
      return self.summary()
    return self.summary() + ' (lent to ' + self.borrower_name() + ')'
    
  def borrower_name(self):
    try:
      return self.borrower.display_name()
    except AttributeError:
      return str(None)
  
  def transitions(self):
    links = ''
    if self.belongs_to_me():
      links += (' <a href="/lend/' + str(self.key()) + '">lend</a>')
      links += (' <a href="/delete/' + str(self.key()) + '">delete</a>')
    elif self.borrowed_by_me():
      links += (' <a href="/return/' + str(self.key()) + '">return</a>')
    elif self.belongs_to_someone_else():
      links += (' <a href="/borrow/' + str(self.key()) + '">borrow</a>')
    return links

  def transition_if_borrowable(self):
    links = ''
    if self.belongs_to_someone_else() and self.is_available():
      links += (' <a href="/borrow/' + str(self.key()) + '">borrow</a>')
    return links
    
  def is_available(self):
    return None == self.borrower

  def is_lent(self):
    return None != self.borrower

  def belongs_to_someone_else(self):
    return users.get_current_user() != self.owner.googleUser
    
  def belongs_to_me(self):
    return users.get_current_user() == self.owner.googleUser
    
  def borrowed_by_me(self):
    if self.borrower:
      return users.get_current_user() == self.borrower.googleUser
    return False
    
  def change_borrower(self, new_borrower):
    self.borrower = new_borrower
  
  def return_to_owner(self):
    self.change_borrower(None)
    
  def obliterate(self):
    if self.belongs_to_me():
      self.delete()
  
###################################################################  