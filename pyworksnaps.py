#!/usr/bin/env python
'''
See http://worksnaps.net/webhelp/webservice_api/

'''
import urllib2
import time
from base64 import b64encode
from dateutil.parser import parse as parseDate
from xml.dom.minidom import parseString


class WorksnapsError(Exception):
    pass


class WorksnapsConnectionError(WorksnapsError):
    pass


instance_classes = []
class WorksnapsItemGetterable(type):
    def __init__( klass, name, bases, attrs ):
        super(WorksnapsItemGetterable,klass).__init__(name,bases,attrs)
        instance_classes.append( klass )


class WorksnapsItemBase(object):
    def __init__( self, worksnaps, data={}):
        self.worksnaps = worksnaps
        for key,value in data.items():
            key = key.replace('-','_').replace(' ','_')
            try:
                setattr( self, key, value )
            except AttributeError:
                pass


class User(WorksnapsItemBase):
    __metaclass__ = WorksnapsItemGetterable

    base_url = '/users'
    element_name = 'user'
    plural_name = 'users'

    def __unicode__(self):
        return u'User: %s %s' % (self.first_name, self.last_name)

    def entries(self,start,end):
        return self.worksnaps._time_entries( '%s/%d/' % (self.base_url, self.id), start, end )


class Project(WorksnapsItemBase):
    __metaclass__ = WorksnapsItemGetterable

    base_url = '/projects'
    element_name = 'project'
    plural_name = 'projects'

    def __unicode__(self):
        return 'Project: ' + self.name

    def tasks(self):
        return self.worksnaps._tasks('%s/%s/' % (self.base_url, self.id))

    def task(self, task_id):
        return self.worksnaps.task('%s/tasks/%s' % (self.id, task_id))

    def entries(self,start,end):
        return self.worksnaps._time_entries( '%s/%s/' % (self.base_url, self.id), start, end )


class Task(WorksnapsItemBase):
    __metaclass__ = WorksnapsItemGetterable

    base_url = '/projects'
    element_name = 'task'
    plural_name = 'tasks'

    def __unicode__(self):
        return 'Task: ' + self.name


class Entry(WorksnapsItemBase):
    def __unicode__(self):
        return '%0.02f hours for project %d' % (self.hours, self.project_id)

    @property
    def user(self):
        return self.worksnaps.user( self.user_id )

    @property
    def project(self):
        return self.worksnaps.project( self.project_id )

    @property
    def task(self):
        return self.worksnaps.task( '%s/tasks/%s' % (self.project_id, self.task_id))


class Worksnaps(object):
    uri = 'https://www.worksnaps.net/api'

    def __init__(self,token):
        self.token = token
        self.headers={
            'Authorization':'Basic '+b64encode('%s:%s' % (token,'')),
            'Accept':'application/xml',
            'Content-Type':'application/xml',
            'User-Agent':'worksnaps.py',
        }

        # create getters
        for klass in instance_classes:
            self._create_getters( klass )

    def _create_getters(self,klass):
        '''
        This method creates both the singular and plural getters for various
        Worksnaps object classes.

        '''
        flag_name = '_got_' + klass.element_name
        cache_name = '_' + klass.element_name

        setattr( self, cache_name, {} )
        setattr( self, flag_name, False )

        cache = getattr( self, cache_name )

        def _get_item(id):
            if id in cache:
                return cache[id]
            else:
                url = '%s/%s.xml' % (klass.base_url, id)
                item = self._get_element_values( url, klass.element_name ).next()
                item = klass( self, item )
                cache[id] = item
                return item

        setattr( self, klass.element_name, _get_item )

        def _get_items():
            if getattr( self, flag_name ):
                for item in cache.values():
                    yield item
            else:
                for element in self._get_element_values( klass.base_url, klass.element_name ):
                    item = klass( self, element )
                    cache[ item.id ] = item
                    yield item

                setattr( self, flag_name, True )

        setattr( self, klass.plural_name, _get_items )

    def _time_entries(self,root,start,end):
        url = root + 'reports?name=time_entries&from_timestamp=%d&to_timestamp=%d' % (int(time.mktime(start.timetuple())), int(time.mktime(end.timetuple())))

        for element in self._get_element_values( url, 'time_entry' ):
            yield Entry( self, element )

    def _tasks(self, root):
        url = root + 'tasks.xml'

        for element in self._get_element_values( url, 'task' ):
            yield Task( self, element )

    def _request(self,url,data=None):
        if data:
            request = urllib2.Request( url=self.uri+url, data=data, headers=self.headers)
        else:
            request = urllib2.Request( url=self.uri+url, headers=self.headers )

        try:
            r = urllib2.urlopen(request)
            xml = r.read()
            return parseString(xml)
        except urllib2.URLError:
            raise
            #raise WorksnapsConnectionError()

    def _get_element_values(self,url,tagname):
        def get_element(element):
            text = ''.join( n.data for n in element.childNodes if n.nodeType == n.TEXT_NODE )
            try:
                entry_type = element.getAttribute('type')
                if entry_type == 'integer':
                    try:
                        return int( text )
                    except ValueError:
                        return 0
                elif entry_type in ('date','datetime'):
                    return parseDate( text )
                elif entry_type == 'boolean':
                    try:
                        return text.strip().lower() in ('true', '1')
                    except ValueError:
                        return False
                elif entry_type == 'decimal':
                    try:
                        return float( text )
                    except ValueError:
                        return 0.0
                else:
                    return text
            except:
                return text

        xml = self._request(url)
        for entry in xml.getElementsByTagName(tagname):
            value = {}
            for attr in entry.childNodes:
                if attr.nodeType == attr.ELEMENT_NODE:
                    tag = attr.tagName
                    value[tag] = get_element( attr )

            if value:
                yield value
