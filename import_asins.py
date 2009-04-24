# from http://dalelane.co.uk/blog/?p=303

import os
import urllib
import urllib2
import cookielib
import getpass

print "***Need to authenticate with Google. Credentials not stored, only relayed.***\n***Please make sure you have asins.csv in the current directory***"
users_email_address = raw_input("Google/Gmail account id (e.g myemail@gmail.com): ")
users_password      = getpass.getpass()

target_authenticated_google_app_engine_uri = 'http://whotookmybook.appspot.com/mybooks'
my_app_name = "whotookmybook"

# we use a cookie to authenticate with Google App Engine
#  by registering a cookie handler here, this will automatically store the
#  cookie returned when we use urllib2 to open http://currentcost.appspot.com/_ah/login
cookiejar = cookielib.LWPCookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
urllib2.install_opener(opener)

#
# get an AuthToken from Google accounts
#
auth_uri = 'https://www.google.com/accounts/ClientLogin'
authreq_data = urllib.urlencode({ "Email":   users_email_address,
                                  "Passwd":  users_password,
                                  "service": "ah",
                                  "source":  my_app_name,
                                  "accountType": "GOOGLE" })
auth_req = urllib2.Request(auth_uri, data=authreq_data)
auth_resp = urllib2.urlopen(auth_req)
auth_resp_body = auth_resp.read()
# print "auth resp body is..."
# print auth_resp_body
# auth response includes several fields - we're interested in
#  the bit after Auth=
auth_resp_dict = dict(x.split("=")
                      for x in auth_resp_body.split("\n") if x)
authtoken = auth_resp_dict["Auth"]

#
# get a cookie
#
#  the call to request a cookie will also automatically redirect us to the page
#   that we want to go to
#  the cookie jar will automatically provide the cookie when we reach the
#   redirected location

# this is where I actually want to go to
serv_uri = target_authenticated_google_app_engine_uri

serv_args = {}
serv_args['continue'] = serv_uri
serv_args['auth']     = authtoken

full_serv_uri = "http://whotookmybook.appspot.com/_ah/login?%s" % (urllib.urlencode(serv_args))
#just read it to move on. since can't redirect POST 
urllib2.urlopen(full_serv_uri).read()
try:
  asin_file = open("asins.csv")
  asins = asin_file.readline()
  asin_file.close()
  print "importing asins:"
  post_body = "asins=" + asins.strip()
  print post_body
  serv_resp = urllib2.urlopen("http://whotookmybook.appspot.com/asin-import", data = post_body)
  serv_resp_body = serv_resp.read()
  print serv_resp_body
except:
  print "Error reading asins.csv"
  raise
