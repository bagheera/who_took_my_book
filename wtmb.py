from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import mail

from datetime import datetime, date, timedelta
import cgi
import logging
from eventregistry import *
from wtmbsearch import Searchable
###################################################################
WTMB_SENDER = "whotookmybook@gmail.com"
#from http://code.activestate.com/recipes/52282/#c2
def ternary(condition, trueVal, falseVal):
    if condition:
        return trueVal
    else:
        return falseVal

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

class WtmbException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
###################################################################
class AppUser(db.Model):
    googleUser = db.UserProperty()
    wtmb_nickname = db.StringProperty()
    unregistered_email = db.StringProperty()
    created_date = db.DateTimeProperty(auto_now_add="true")
    last_login_date = db.DateTimeProperty(auto_now="true")
    member_of = db.StringListProperty(default=['rest_of_the_world']) # not visible in db if empty

    def __eq__(self, other):
        return self.googleUser == other.googleUser

    def __ne__(self, other):
        return not self.__eq__(other)
    
    def book_count(self):
        return Book.gql("WHERE owner=:1", self).count()
        
    def is_outsider(self):
        return not self.googleUser

    @staticmethod
    def create_outsider(name, for_book, email=None):
        if not name or name.strip() == "":
            raise ValueError("Name cannot be empty")
        if AppUser.gql('WHERE googleUser = :1 and wtmb_nickname= :2', None, name).get():
            raise ValueError("This name is taken")
        new_user = AppUser(wtmb_nickname=name, unregistered_email=email, member_of = for_book.owner.member_of)
        new_user.put()
        NewOutsider({'outsider':new_user, 'for_book':for_book}).fire()
        return new_user

    @classmethod
    def on_new_user_registration(cls, new_user):
        try:
            import os
            from google.appengine.ext.webapp import template
            path = os.path.join(os.path.dirname(__file__), 'welcome.template')
            welcome_msg = template.render(path, {})
            mail.send_mail(
                         sender=WTMB_SENDER,
                         to=new_user.email(),
                         cc=WTMB_SENDER,
                         subject='[whotookmybook] Welcome',
                         body=welcome_msg)
        except Exception, e:
            logging.error(str(e))

    @staticmethod
    def getAppUserFor(aGoogleUser, outsider_key=None, outsider_email=None):
        appuser = AppUser.gql('WHERE googleUser = :1', aGoogleUser).get()
        if appuser is None:
            if outsider_key and outsider_email and AppUser.get(outsider_key) and AppUser.get(outsider_key).unregistered_email == outsider_email:
                appuser = AppUser.get(outsider_key).regularize()
            else:
                current_user = users.get_current_user()
                appuser = AppUser(googleUser=current_user, wtmb_nickname=current_user.nickname())
                appuser.put()
                NewUserRegistered(appuser).fire()
        return appuser

    def regularize(self):
        self.googleUser = users.get_current_user()
        self.put()
        NewUserRegistered(self).fire()
        return self

    def display_name(self):
        return self.wtmb_nickname if self.wtmb_nickname else self.googleUser.nickname()

    def email(self):
        if self.googleUser:
            return self.googleUser.email()
        if self.unregistered_email:
            return self.unregistered_email
        else:
            return "whotookmybook+unregistered_user_" + self.wtmb_nickname + "@gmail.com"

    def change_nickname(self, new_nick):
        self.wtmb_nickname = new_nick
        self.put()

    def update_last_login(self):
        self.put()

    def to_hash(self):
        return {
                                 "nickname": self.display_name(),
                                 "email": self.email(),
                                 "last_login": self.last_login_date.toordinal() #isoformat() + 'Z'
                                        }
    def matches(self, fragment):
        fragment = fragment.upper()
        return self.email().upper().find(fragment) != -1 or self.display_name().upper().find(fragment) != -1
    
    def friend_of(self, other):
        for group in self.member_of:
            if group in other.member_of:
                return True
        return False
    
    def setMembership(self, groups):
        if len(groups) == 0:
            groups = ['rest_of_the_world'] 
        self.member_of = groups
        self.put()
        MembershipChanged({"new_groups": groups, "owner_key":str(AppUser.me().key())}).fire()

    def belongs_to(self, group):
        return group in self.member_of
    
    def purge(self):
        logging.warning("Purging user: "+ self.display_name())
        self.delete()
    
    def hasnt_transacted(self):
        return self.books_owned.get() is None and self.books_borrowed.get() is None
    
    def just_created(self):
        return datetime.utcnow() - self.created_date < timedelta(0,4,0)
    
    @staticmethod
    def me():
        return AppUser.gql('WHERE googleUser = :1', users.get_current_user()).get()

    @staticmethod
    def others():
        me = AppUser.me()
        my_key = me.key()
        for user in AppUser.gql("ORDER BY last_login_date DESC"):
            if user.key() != my_key and me.friend_of(user):
                yield user

    @staticmethod
    def on_new_outsider(info):
        outsider = info['outsider']
        if outsider.unregistered_email:
            book = info['for_book']
            #current thread coupling - bad
            import urllib
            msg_text = "Hi " + outsider.display_name() + \
                                "\nI just made use of a free app called who_took_my_book to track that I have lent the book '" + book.summary() + \
                                "' to you.\nIf you'd like to register for this app to keep track of your books, just click http://whotookmybook.appspot.com/mybooks?u=" + \
                                str(outsider.key()) + '&e=' + urllib.quote(outsider.unregistered_email)
            logging.debug(msg_text)
            try:
                mail.send_mail(
                             sender=AppUser.me().email(),
                             to=outsider.unregistered_email,
                             cc=(WTMB_SENDER, AppUser.me().email()),
                             subject='Invitation to who_took_my_book',
                             body=msg_text)
            except Exception, e:
                logging.error(str(e))

    @staticmethod
    def active_users():
      threeMonthsAgo = date.today() - timedelta(days=90)
      return db.GqlQuery("SELECT __key__ from AppUser WHERE last_login_date > :1", threeMonthsAgo).fetch(1000)

NewUserRegistered().subscribe(AppUser.on_new_user_registration)
NewOutsider().subscribe(AppUser.on_new_outsider)
###################################################################        
class Book(db.Model, Searchable):
    author = db.StringProperty()
    owner = db.ReferenceProperty(AppUser, collection_name="books_owned")
    title = db.StringProperty()
    borrower = db.ReferenceProperty(AppUser, collection_name="books_borrowed", required=False)
    asin = db.StringProperty()
    is_technical = db.BooleanProperty()
    dewey = db.StringProperty()
    created_date = db.DateTimeProperty(auto_now_add="true")
    INDEX_ONLY = ['author', 'title']

    def __init__(self, parent=None, key_name=None, **kw):
        super(Book, self).__init__(parent, key_name, **kw)
        if self.title.strip() == "":
            raise BookWithoutTitle("Title required")
        if self.author.strip() == "":
            self.author = "unknown"

    def to_hash(self):
        return {
                                        "title": cgi.escape(self.title),
                                        "author":cgi.escape(self.author),
                                        "is_tech": self.is_technical,
                                        "dewey": self.dewey,
                                        "borrowed_by": cgi.escape(self.borrower_name()),
                                        "owner": cgi.escape(self.owner.display_name()),
                                        "owner_groups": ','.join(self.owner.member_of),
                                        "key": str(self.key()),
                                        "asin":self.asin,
                                        "added_on": self.created_date.toordinal()
                                        }

    def summary(self):
        return self.title + ' by ' + self.author

    def borrower_name(self):
        try:
            return self.borrower.display_name()
        except AttributeError:
            return str(None)

    def is_available(self):
        return self.borrower is None

    def is_lent(self):
        return self.borrower is not None

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
        self.index()
        NewBookAdded(self).fire()
        return self

    def return_to_owner(self):
        if self.borrowed_by_me() or self.belongs_to_me():
            old_borrower = self.borrower
            self.__change_borrower(None)
            self.put()
            BookReturned({'book':self, 'returner': AppUser.me(), 'old_borrower': old_borrower}).fire()
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to return" + self.title + " owned by " + self.owner.display_name())
            raise IllegalStateTransition("illegal attempt to return")

    def obliterate(self):
        if self.belongs_to_me():
            info = {'book_key': str(self.key()), 'owner': str(self.owner.key())}
            if self.borrower:
                info['old_borrower'] = str(self.borrower.key())
            self.delete()
            BookDeleted(info).fire()
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to delete " + self.title + " owned by " + self.owner.display_name())
            raise IllegalStateTransition("illegal attempt to delete")

    def borrow(self):
        if self.belongs_to_someone_else() and self.is_available():
            self.__change_borrower(AppUser.me())
            self.put()
            BookBorrowed(self).fire()
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to borrow " + self.title + " owned by " + self.owner.display_name())
            raise IllegalStateTransition("illegal attempt to borrow")

    def lend_to(self, appuser):
        if self.belongs_to_me():
            if not self.is_available():
                self.return_to_owner()
            self.__change_borrower(appuser)
            self.put()
            BookLent(self).fire()
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to lend " + self.title + " owned by " + self.owner.display_name() + " to " + appuser.display_name())
            raise IllegalStateTransition("illegal attempt to lend")

    def remind(self):
        if self.belongs_to_me() and self.is_lent():
            mail.send_mail(
                     sender=AppUser.me().email(),
                     to=self.borrower.email(),
                     cc=(WTMB_SENDER, AppUser.me().email()),
                     subject='[whotookmybook] ' + self.title,
                     body="Hi " + self.borrower.display_name() + "\n" \
                        + self.owner.display_name() + " would like to gently remind you to return '" + self.title + "' if you have finished with it. \n email sent by http://whotookmybook.appspot.com")
        else:
            logging.error(AppUser.me().display_name() + "made an illegal attempt to remind about " + self.title + " owned by " + self.owner.display_name())
            raise WtmbException("illegal attempt to remind")
    
    @staticmethod
    def all_books():
        return db.GqlQuery('SELECT __key__ from Book  ORDER BY created_date DESC LIMIT 1000'  ).fetch(1000)
        
    @staticmethod
    def owned_by(appuser_key):
        return db.GqlQuery("SELECT __key__ from Book WHERE owner = :1 LIMIT 1000", appuser_key).fetch(1000)

    @staticmethod
    def borrowed_by(appuser_key):
        return db.GqlQuery("SELECT __key__ from Book WHERE borrower = :1 LIMIT 1000", appuser_key).fetch(1000)

    @staticmethod
    def unlent_by(appuser_key):
        return db.GqlQuery("SELECT __key__ from Book WHERE owner = :1 AND borrower = NULL  LIMIT 1000", appuser_key).fetch(1000)

    @staticmethod
    def new_books():
      last_week = date.today() - timedelta(days=7)
      return db.GqlQuery("SELECT __key__ from Book WHERE created_date > :1", last_week).fetch(1000)


    @staticmethod
    def on_return(info):
        returner = info['returner']
        book = info['book']
        old_borrower = info['old_borrower']
        message = None
        if (returner != book.owner):
            message = " has returned this book to " + book.owner.display_name()
        else: 
            message = returner.display_name() + " has reclaimed this book"

        mail.send_mail(
                     sender=AppUser.me().email(),
                     to=book.owner.email(),
                     cc=(WTMB_SENDER, AppUser.me().email()),
                     subject='[whotookmybook] ' + book.title,
                     body=message)
        from bookcache import CachedBook, CacheBookIdsBorrowed
        book_key_str = str(book.key())
        CacheBookIdsBorrowed.remove_book(str(old_borrower.key()), book_key_str)
        CachedBook.reset(book_key_str)

    @staticmethod
    def on_borrow(book):
        mail.send_mail(
                 sender=AppUser.me().email(),
                 to=book.owner.email(),
                 cc=(WTMB_SENDER, AppUser.me().email()),
                 subject='[whotookmybook] ' + book.title,
                 body="Hi " + book.owner.display_name() + "\n" + book.borrower.display_name()
                 + " has requested or borrowed this book from you. \n email sent by http://whotookmybook.appspot.com")
        from bookcache import CachedBook, CacheBookIdsBorrowed
        book_key_str = str(book.key())
        CacheBookIdsBorrowed.add_book(str(book.borrower.key()), book_key_str)
        CachedBook.reset(book_key_str)

    @staticmethod
    def on_lent(book):
        mail.send_mail(
                     sender=AppUser.me().email(),
                     to=book.borrower.email(),
                     cc=(WTMB_SENDER, AppUser.me().email()),
                     subject='[whotookmybook] ' + book.title,
                     body=book.owner.display_name() + " has lent this book to " + book.borrower.display_name())
        from bookcache import CachedBook, CacheBookIdsBorrowed
        book_key_str = str(book.key())
        CacheBookIdsBorrowed.add_book(str(book.borrower.key()), book_key_str)
        CachedBook.reset(book_key_str)

    @staticmethod
    def on_add(book):
        from bookcache import CacheBookIdsOwned, CachedFeed
        book_key_str = str(book.key())
        CacheBookIdsOwned.add_book(str(book.owner.key()), book_key_str)
        CachedFeed.reset()

    @staticmethod
    def on_delete(info):
        book_key_str = info['book_key']
        old_borrower = info.get('old_borrower', None)
        owner = info['owner']
        from bookcache import CacheBookIdsOwned, CacheBookIdsBorrowed, CachedBook
        CacheBookIdsOwned.remove_book(owner, book_key_str)
        CachedBook.reset(book_key_str)
        if old_borrower:
            CacheBookIdsBorrowed.remove_book(old_borrower, book_key_str)

BookReturned().subscribe(Book.on_return)
BookLent().subscribe(Book.on_lent)
NewBookAdded().subscribe(Book.on_add)
BookDeleted().subscribe(Book.on_delete)
BookBorrowed().subscribe(Book.on_borrow)
###################################################################
class Group(db.Model):
    name = db.StringProperty()
    createdBy = db.StringProperty()
    description = db.StringProperty()