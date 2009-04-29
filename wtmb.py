from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import mail
from django.utils import simplejson

import logging
###################################################################
WTMB_SENDER = "whotookmybook@gmail.com"
class IllegalStateTransition(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class AppUser(db.Model):
    googleUser = db.UserProperty()
    wtmb_nickname = db.StringProperty()

    @staticmethod
    def getAppUserFor(aGoogleUser):
        appuser = AppUser.gql('WHERE googleUser = :1', aGoogleUser).get()
        if appuser is None:
            appuser = AppUser(googleUser = users.get_current_user())
            appuser.put()
            #bad place for mail
            mail.send_mail(
                         sender = WTMB_SENDER,
                         to = [users.get_current_user().email()],
                         cc = WTMB_SENDER,
                         subject = '[whotookmybook] Welcome',
                         body = "Thanks for choosing to use http://whotookmybook.appspot.com")
        return appuser

    def display_name(self):
        return self.googleUser.nickname()

    def email(self):
        return self.googleUser.email()

    @staticmethod
    def me():
        return AppUser.gql('WHERE googleUser = :1', users.get_current_user()).get()

    @staticmethod
    def others():
        return AppUser.gql('WHERE googleUser != :1', users.get_current_user())
###################################################################        
class Book(db.Model):
    author = db.StringProperty()
    owner = db.ReferenceProperty(AppUser, collection_name = "books_owned")
    title = db.StringProperty()
    borrower = db.ReferenceProperty(AppUser, collection_name = "books_borrowed", required = False)
    uniq = db.StringProperty()
    is_technical = db.BooleanProperty()

    def __init__(self, parent = None, key_name = None, **kw):
        super(Book, self).__init__(parent, key_name, **kw)
        if not self.uniq:
            uniq_separator = "_#.,^_"
            self.uniq = self.title + uniq_separator + self.author

    def to_json(self):
        return simplejson.dumps({
                                        "title": self.title,
                                        "author":self.author,
                                        "is_tech": self.is_technical,
                                        "borrowed_by": self.borrower_name(),
                                        "owner": self.owner.display_name(),
                                        "key": str(self.key())
                                        })

    def summary(self):
        return self.title + ' by ' + self.author

    def borrower_name(self):
        try:
            return self.borrower.display_name()
        except AttributeError:
            return str(None)

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

    def __change_borrower(self, new_borrower):
        self.borrower = new_borrower

    def return_to_owner(self):
        if self.borrowed_by_me():
            self.__change_borrower(None)
            self.put()
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to return" + self.title + " owned by " + self.owner.display_name())
            raise IllegalStateTransition("illegal attempt to return")

    def obliterate(self):
        if self.belongs_to_me():
            self.delete()
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to delete " + self.title + " owned by " + self.owner.display_name())
            raise IllegalStateTransition("illegal attempt to delete")

    def borrow(self):
        if self.belongs_to_someone_else() and self.is_available():
            self.__change_borrower(AppUser.me())
            self.put()
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to borrow " + self.title + " owned by " + self.owner.display_name())
            raise IllegalStateTransition("illegal attempt to borrow")

    def lend_to(self, appuser):
        if self.belongs_to_me():
            self.__change_borrower(appuser)
            self.put()
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to lend " + self.title + " owned by " + self.owner.display_name() + " to " + appuser.display_name())
            raise IllegalStateTransition("illegal attempt to lend")

    @staticmethod
    def my_books():
        return Book.gql("WHERE owner = :1", AppUser.me())

    @staticmethod
    def borrowed_books():
        return Book.gql("WHERE borrower = :1", AppUser.me())

    @staticmethod
    def others_books():
        return Book.gql("WHERE owner != :1 ORDER BY owner", AppUser.me())
###################################################################
