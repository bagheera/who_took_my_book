from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import mail

from django.utils import simplejson
import cgi
import logging
###################################################################
WTMB_SENDER = "whotookmybook@gmail.com"
class IllegalStateTransition(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class DuplicateBook(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class BookWithoutTitle(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
###################################################################
class AppUser(db.Model):
    googleUser = db.UserProperty()
    wtmb_nickname = db.StringProperty()
    created_date = db.DateTimeProperty(auto_now_add = "true")

    def is_outsider(self):
        return not self.googleUser

    @staticmethod
    def create_outsider(name):
        if not name or name.strip() == "":
            raise ValueError("Name cannot be empty")
        if AppUser.gql('WHERE googleUser = :1 and wtmb_nickname= :2', None, name).get():
            raise ValueError("This name is already taken")
        new_user = AppUser(wtmb_nickname = name)
        new_user.put()
        return new_user

    @staticmethod
    def getAppUserFor(aGoogleUser):
        appuser = AppUser.gql('WHERE googleUser = :1', aGoogleUser).get()
        if appuser is None:
            current_user = users.get_current_user()
            appuser = AppUser(googleUser = current_user, wtmb_nickname = current_user.nickname())
            appuser.put()
            #bad place for mail
            mail.send_mail(
                         sender = WTMB_SENDER,
                         to = [current_user.email()],
                         cc = WTMB_SENDER,
                         subject = '[whotookmybook] Welcome',
                         body = "Thanks for choosing to use http://whotookmybook.appspot.com")
        return appuser

    def display_name(self):
        return self.wtmb_nickname if self.wtmb_nickname else self.googleUser.nickname()

    def email(self):
        return self.googleUser.email() if self.googleUser else "whotookmybook+unregistered_user_" + self.wtmb_nickname + "@gmail.com"

    def change_nickname(self, new_nick):
        self.wtmb_nickname = new_nick
        self.put()

    def to_json(self):
        return simplejson.dumps({
                                 "nickname": self.display_name(),
                                 "email": self.email()
                                        })

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
    asin = db.StringProperty()
    is_technical = db.BooleanProperty()
    created_date = db.DateTimeProperty(auto_now_add = "true")

    def __init__(self, parent = None, key_name = None, **kw):
        super(Book, self).__init__(parent, key_name, **kw)
        if self.title.strip() == "":
            raise BookWithoutTitle("Title required")
        if self.author.strip() == "":
            self.author = "unknown"

    def to_json(self):
        return simplejson.dumps({
                                        "title": cgi.escape(self.title),
                                        "author":cgi.escape(self.author),
                                        "is_tech": self.is_technical,
                                        "borrowed_by": cgi.escape(self.borrower_name()),
                                        "owner": cgi.escape(self.owner.display_name()),
                                        "key": str(self.key()),
                                        "asin":self.asin,
                                        "added_on": self.created_date.isoformat() + 'Z'
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

    def __duplicate(self):
        return bool(db.GqlQuery("SELECT __key__ from Book WHERE owner = :1 and title =:2 and author = :3", AppUser.me().key(), self.title, self.author).get())

    def create(self):
        if self.__duplicate():
            raise DuplicateBook("Add failed: You (" + AppUser.me().display_name() + ") already have added '" + self.title + "'");
        self.put()
        return self

    def return_to_owner(self):
        if self.borrowed_by_me() or self.belongs_to_me():
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
    def owned_by(appuser_key):
        return db.GqlQuery("SELECT __key__ from Book WHERE owner = :1 LIMIT 1000", appuser_key).fetch(1000)

    @staticmethod
    def borrowed_by(appuser_key):
        return db.GqlQuery("SELECT __key__ from Book WHERE borrower = :1 LIMIT 1000", appuser_key).fetch(1000)

    @staticmethod
    def new_books():
      from datetime import date, timedelta
      last_week = date.today() - timedelta(days = 7)
      return db.GqlQuery("SELECT __key__ from Book WHERE created_date > :1", last_week).fetch(1000)
###################################################################
