import cgi
import wsgiref.handlers
import os
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from wtmb import *
from bookactions import *
from bookcache import *
from full import *

class BookListPage(webapp.RequestHandler):
  def get(self, *args):
    if self.request.path_info != '/mybooks':
       self.redirect('/mybooks')
    user = users.get_current_user()
    if user:
      url = users.create_logout_url("/mybooks")
      url_linktext = 'Logout'
      me = AppUser.getAppUserFor(user) #registers new user
      me.update_last_login()
      template_values = {
        'url': url,
        'url_linktext': url_linktext,
        "username": me.display_name()
      }
      path = os.path.join(os.path.dirname(__file__), 'books.html')
      self.response.out.write(template.render(path, template_values)) # render o/p can be cached
    else:
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'
      self.redirect(users.create_login_url(self.request.uri))
###################################################################    
class LendPage(webapp.RequestHandler):
  def get(self, what):
    members = [[str(user.key()), user.display_name() + " (" + user.email() + ")"] for user in AppUser.others()]
    members.sort(lambda x, y: cmp(x[1].lower(), y[1].lower()))
    template_values = {
      'book': Book.get(db.Key(what)),
      'members': members,
    }
    path = os.path.join(os.path.dirname(__file__), 'lend.html')
    self.response.out.write(template.render(path, template_values))

###################################################################    
class WhatsNewFeed(webapp.RequestHandler):
  def get(self):
    self.response.headers['content-type'] = "application/atom+xml"
    self.response.out.write(CachedFeed.get())

def real_main():
  application = webapp.WSGIApplication(
                                       [(r'/lookup_amz(.*)', Suggest),
                                        ('/mybooks', BookListPage),
                                        ('/addBook', AddToBookshelf),
                                        (r'/delete/(.*)', DeleteBook),
                                        (r'/borrow/(.*)', Borrow),
                                        (r'/return/(.*)', ReturnBook),
                                        (r'/lend/(.*)', LendPage),
                                        (r'/lendTo', LendTo),
                                        ('/mybooksj', FullListing),
                                        ('/asin-import', ImportASINs),
                                        ('/nickname', Nickname),
                                        ('/feed/whats_new', WhatsNewFeed),
                                        (r'(/?)(.*)', BookListPage)],
                                       debug = True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  real_main()
