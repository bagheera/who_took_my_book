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
      logging.info('creating logout url for ' + user.nickname())
      url = users.create_logout_url("/mybooks")
      logging.debug(url)
      url_linktext = 'Logout'
      current_appuser = AppUser.getAppUserFor(user) #registers new user
      others = current_appuser.others()
      template_values = {
        'others': others,
        'current_user': current_appuser,
        'url': url,
        'url_linktext': url_linktext
#        'nickname': NickName().wtmb_name_for(current_appuser)
        }
      path = os.path.join(os.path.dirname(__file__), 'books.html')
      self.response.out.write(template.render(path, template_values)) # render o/p can be cached
    else:
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'
      self.redirect(users.create_login_url(self.request.uri))
###################################################################
# putting this on hold  
#class NickName:
#    def wtmb_name_for(self, some_user):
#        if some_user.display_name() is None:
#            return '<input type="text" id="nickname" value="" title="In case you&apos;d like to be referred by a name different from your userid"/><a href="/nickname"> Set Nickname</a>
#        else:
#            return some_user.display_name()
###################################################################  

def real_main():
  application = webapp.WSGIApplication(
                                       [(r'/lookup_amz(.*)', Suggest),
                                        ('/mybooks', BookListPage),
                                        ('/addBook', AddToBookshelf),
                                        (r'/delete/(.*)', DeleteBook),
                                        (r'/borrow/(.*)', Borrow),
                                        (r'/return/(.*)', ReturnBook),
                                        (r'/lend/(.*)', Lend),
                                        (r'/lendTo/(.*)', LendTo),
                                        ('/mybooksj', FullListing),
                                        ('/asin-import', ImportASINs),
                                        (r'(/?)(.*)', BookListPage)],
                                       debug = True)
  wsgiref.handlers.CGIHandler().run(application)

def profile_main():
 # This is the main function for profiling 
 # We've renamed our original main() above to real_main()
 import cProfile, pstats, StringIO
 prof = cProfile.Profile()
 prof = prof.runctx("real_main()", globals(), locals())
 stream = StringIO.StringIO()
 stats = pstats.Stats(prof, stream = stream)
 stats.sort_stats("time")  # Or cumulative
 stats.print_stats(80)  # 80 = how many to print
 # The rest is optional.
 # stats.print_callees()
 # stats.print_callers()
 #logging.debug("Profile data:\n%s", stream.getvalue())
 logging.info(memcache.get_stats())

if __name__ == "__main__":
  real_main()
