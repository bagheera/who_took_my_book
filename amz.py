from xml.dom import minidom
from wtmb import Book
import urllib
from django.utils import simplejson
import logging

class Amz:

    def __init__(self):
        self.amz_ns = 'http://webservices.amazon.com/AWSECommerceService/2008-08-19'

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

    def get_items_from_result(self, responseBodyText):
        dom = minidom.parseString(responseBodyText)
        return dom.getElementsByTagNameNS(self.amz_ns, 'Item')

    def get_attribs_for_items(self, asin_csv):
        return self.amz_call(
                                {'Operation' : 'ItemLookup' ,
                                 'IdType' : 'ASIN' ,
                                 'ItemId' : asin_csv ,
                                 'ResponseGroup' : 'ItemAttributes' })

    def get_books_for_asins(self, asin_lst):
        books = []
        asin_lst = map(lambda asin: unicode.strip(asin).zfill(10), asin_lst)
        result = self.get_attribs_for_items(','.join(asin_lst))
        if result.status == 200:
            items = self.get_items_from_result(result.read())
            for item in items:
                try:
                    bk_title = self.__title_of(item)
                    bk_author = self.__author_of(item)
                    bk_asin = self.__asin_of(item)
                    is_tech = False
                    dewey_decimal = self.__dewey_decimal_of(item)
                    is_tech = self.is_tech_dewey(dewey_decimal)
                    book = Book(title=bk_title, author=bk_author, is_technical=is_tech, asin=bk_asin, dewey=dewey_decimal)
                    books.append(book)
                except:
                  pass
        else:
            logging.info("Did you enter comma separated ASINs?\namz lookup failed with code " + str(result.status))
        return books

    def get_dewey(self, asin):
        if asin == '0':
            return None
        try:
            result = self.get_attribs_for_items(asin)
            if result.status == 200:
                item = self.get_items_from_result(result.read())[0]
                return self.__dewey_decimal_of(item)
        except:
            logging.error("exception in dewey lookup")
            return None

    def search_by(self, searchString):
        result = self.amz_call(
                                {'Operation' : 'ItemSearch' ,
                                 'Keywords' : urllib.unquote(searchString) ,
                                 'SearchIndex' : 'Books' ,
                                 'ResponseGroup' : 'Small' })
        list = []
        if result.status == 200:
            responseBodyText = result.read(result.fp.len)
            for item in self.get_items_from_result(responseBodyText):
               asin = self.__asin_of(item)
               node = item.getElementsByTagNameNS(self.amz_ns, 'ItemAttributes')[0]
               title = self.__title_of(node)
               author = self.__author_of(node)
               if not author:
                   author = 'unknown'
               list.append(simplejson.dumps({ "id" : asin , "value" : title , "info" : author}))
        return list

    keyFile = open('accesskey.secret', 'r')
    AWS_SECRET_ACCESS_KEY = keyFile.read()
    keyFile.close()
    def amz_call(self, call_params):

        AWS_ACCESS_KEY_ID = '1PKXRTEQQV19XXDW3ZG2'
        AWS_ASSOCIATE_TAG = 'whotookmybook-20'

        import time
        from boto.connection import AWSQueryConnection
        aws_conn = AWSQueryConnection(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Amz.AWS_SECRET_ACCESS_KEY, is_secure=False,
            host='ecs.amazonaws.com')
        aws_conn.SignatureVersion = '2'
        base_params = dict(
            Service='AWSECommerceService',
            Version='2008-08-19',
            SignatureVersion=aws_conn.SignatureVersion,
            AWSAccessKeyId=AWS_ACCESS_KEY_ID,
            AssociateTag=AWS_ASSOCIATE_TAG,
            Timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()))
        #http://stackoverflow.com/questions/38987/how-can-i-merge-two-python-dictionaries-as-a-single-expression
        params = dict(base_params, **call_params)
        verb = 'GET'
        path = '/onca/xml'
        qs, signature = aws_conn.get_signature(params, verb, path)
        qs = path + '?' + qs + '&Signature=' + urllib.quote(signature)
        return aws_conn._mexe(verb, qs, None, headers={})
###################################################################
