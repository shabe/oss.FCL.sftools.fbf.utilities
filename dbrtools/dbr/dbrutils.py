# Copyright (c) 2009 Symbian Foundation Ltd
# This component and the accompanying materials are made available
# under the terms of the License "Eclipse Public License v1.0"
# which accompanies this distribution, and is available
# at the URL "http://www.eclipse.org/legal/epl-v10.html".
#
# Initial Contributors:
# Symbian Foundation Ltd - initial contribution.
#
# Contributors:
# mattd <mattd@symbian.org>
#
# Description:
# DBRutils - Module for handling little bits of stuff to do with generating hashes and scaning directories

import re
import os
import sys
import string
import shutil
import time
from os.path import join, isfile, stat
from stat import *

import glob # temporary (I hope) used for grabbing stuf from zip files...
import tempfile


def defaultdb():
  return os.path.join(patch_path_internal(),'baseline.db')

def patchpath():
  return os.path.join(epocroot(),'%s/' % patch_path_internal())

def patch_path_internal():
  return 'epoc32/relinfo'

def exclude_dirs():
    fixpath = re.compile('\\\\')
    leadingslash = re.compile('^%s' % fixpath.sub('/',epocroot()))
    return [string.lower(leadingslash.sub('',fixpath.sub('/',os.path.join(epocroot(),'epoc32/build')))),string.lower(leadingslash.sub('',fixpath.sub('/',patch_path_internal())))]

def exclude_files():
#    return ['\.sym$','\.dll$'] # just testing...
    return ['\.sym$']
    
def epocroot():
    return os.environ.get('EPOCROOT')

def scanenv():
    print 'Scanning local environment'
    directory = os.path.join(epocroot(),'epoc32')
    env = scandir(directory, exclude_dirs(), exclude_files())
    return env

def createzip(files, name):
    tmpfilename = os.tmpnam( )
    print tmpfilename    
    f = open(tmpfilename,'w')
    for file in sorted(files):
        str = '%s%s' % (file,'\n')
        f.write(str)    
    f.close()
    os.chdir(epocroot())
    exestr = '7z a -Tzip -i@%s %s' %(tmpfilename,name)
    print 'executing: >%s<\n' %exestr
    os.system(exestr)
    os.unlink(tmpfilename)

def extractfiles(files, path):
    zips = glob.glob(os.path.join(path, '*.zip'))
    for name in zips:
      extractfromzip(files, name,'')    
        
    
def extractfromzip(files, name, location):
    tmpfilename = os.tmpnam( )
    print tmpfilename
    cwd = os.getcwd();
    os.chdir(os.path.join(epocroot(),location))
    f = open(tmpfilename,'w')
    for file in sorted(files):
        str = '%s%s' % (file,'\n')
        f.write(str)    
    f.close()
    exestr = '7z x -y -i@%s %s >nul' %(tmpfilename,name)
#    exestr = '7z x -y -i@%s %s' %(tmpfilename,name)
    print 'executing: >%s<\n' %exestr
    os.system(exestr)
    os.unlink(tmpfilename)
    os.chdir(cwd)

def deletefiles(files):
    os.chdir(epocroot())
    for file in files:
      print 'deleting %s' %file
      os.unlink(file)
            

def getzippedDB(location):
    db = dict()
    #This is really crude, but will do for now
#    temp = tempfile.NamedTemporaryFile()
#    print temp.name
    #       Date      Time    Attr         Size   Compressed  Name
    #------------------- ----- ------------ ------------  ------------------------
    #2010-03-10 01:02:30 D....            0            0  epoc32
    #2010-03-10 01:02:30 D....            0            0  epoc32\relinfo
    #2010-03-10 00:49:12 .....      2327835       575578  epoc32\relinfo\epoc32_data.md5
    reattribs = re.compile('(\d+-\d+-\d+\s\d+:\d+:\d+)\s+\..+\s+(\d+)\s+\d*\s*(\S.+)')
    fixpath = re.compile('\\\\')

    tmpfilename = os.tmpnam( )
    print tmpfilename    

#    exestr = '7z l -i!epoc32 -x!epoc32/relinfo %s/*.zip >%s' % (path,temp.name)
    exestr = '7z l -i!epoc32 -x!epoc32/relinfo %s/*.zip >%s' % (location,tmpfilename)

    exeresult = os.system(exestr) 
    if(exeresult):
      sys.exit('Fatal error executing: %s\nReported error: %s' % (exestr,os.strerror(exeresult)))
    else:
      temp = open(tmpfilename,'r')           
      for line in temp:
        res = reattribs.match(line)
        if(res):
            entry = dict()
            entry['time'] = int(time.mktime(time.strptime(res.group(1), '%Y-%m-%d %H:%M:%S')))
            entry['size'] = res.group(2)
            entry['md5'] = 'xxx'
            filename = string.lower(fixpath.sub('/',res.group(3))) 
            db[filename] = entry
      temp.close()
      os.unlink(tmpfilename)      
      #now fill with the MD5s...
      md5zip = os.path.join(location,'build_md5.zip')
      print md5zip 
      temp_dir = tempfile.mkdtemp()
      print temp_dir 
      if(os.path.exists(md5zip)):
        files = set();
        files.add('*')
        extractfromzip(files,md5zip,temp_dir)
        globsearch = os.path.join(temp_dir, os.path.join(patch_path_internal(),'*.md5'))
        print globsearch 
        hashes = glob.glob(globsearch)
        for file in hashes:
            print 'Reading: %s\n' % file
            gethashes(db, file, False)
      shutil.rmtree(temp_dir)            
    return db


def generateMD5s(testset):
    db = dict()
    if(len(testset)):
#      print testset
      os.chdir(epocroot())
      tmpfilename = os.tmpnam( )
      print tmpfilename, '\n'
      f = open(tmpfilename,'w')
      for file in testset:
          entry = dict()
          entry['md5'] = 'xxx'
          db[file] = entry
          str = '%s%s' % (file,'\n')
          f.write(str)
      f.close()
      outputfile = os.tmpnam() 
      exestr = 'evalid -f %s %s %s' % (tmpfilename, epocroot(), outputfile)
#      print exestr
      exeresult = os.system(exestr) 
      if(exeresult):
        sys.exit('Fatal error executing: %s\nReported error: %s' % (exestr,os.strerror(exeresult)))
      else:  
        db = gethashes(db,outputfile, False)
        os.unlink(outputfile)
        os.unlink(tmpfilename)
    return db

# Brittle and nasty!!!
def gethashes(db, md5filename, create):
    os.chdir(epocroot())
#    print 'trying to open %s' % md5filename
    file = open(md5filename,'r')
    root = ''
    fixpath = re.compile('\\\\')
    leadingslash = re.compile('^%s' % fixpath.sub('/',epocroot()))

    evalidparse = re.compile('(.+)\sTYPE=(.+)\sMD5=(.+)')
    dirparse = re.compile('Directory:(\S+)')
    for line in file:
        res = evalidparse.match(line)
        if(res):
            filename = "%s%s" % (root,res.group(1))
            filename = string.lower(fixpath.sub('/',leadingslash.sub('',filename)))            
#            print "found %s" % filename
            if(create):
              entry = dict()
              entry['time'] = 'xxx'
              entry['size'] = 'xxx'
              entry['md5'] = res.group(3)
              db[filename] = entry
            else:    
              if(filename in db):
                  db[filename]['md5'] = res.group(3)

        else:
            res = dirparse.match(line)
            if(res):
                if(res.group(1) == '.'):
                    root = ''
                else:
                    root = '%s/' % res.group(1)
            
    file.close()
    return db


def scandir(top, exclude_dirs, exclude_files):
# exclude_dirs must be in lower case...
#    print "Remember to expand the logged dir from", top, "!!!"
    countdown = 0
    env = dict()
    fixpath = re.compile('\\\\')
    leadingslash = re.compile('^%s' % fixpath.sub('/',epocroot()))
    
    ignorestr=''
    for exclude in exclude_files:
      if(len(ignorestr)):
        ignorestr = '%s|%s' % (ignorestr, exclude)
      else:
        ignorestr = exclude    
    ignore = re.compile(ignorestr) 

    for root, dirs, files in os.walk(top, topdown=True):
        for dirname in dirs:
#            print string.lower(leadingslash.sub('',fixpath.sub('/',os.path.join(root,dirname))))
            if(string.lower(leadingslash.sub('',fixpath.sub('/',os.path.join(root,dirname)))) in exclude_dirs):
#              print 'removing: %s' % os.path.join(root,dirname)
              dirs.remove(dirname)
        for name in files:
            filename = os.path.join(root, name)
            statinfo = os.stat(filename)
            fn = string.lower(leadingslash.sub('',fixpath.sub('/',filename)))
#            print '%s\t%s' % (filename, fn);
            if(countdown == 0):
                print '.',
                countdown = 1000
            countdown = countdown-1
            if not ignore.search(fn,1):
              entry = dict()
              entry['time'] = '%d' % statinfo[ST_MTIME]
              entry['size'] = '%d' % statinfo[ST_SIZE]
              entry['md5'] = 'xxx'
              env[fn] = entry
  #            data = [statinfo[ST_MTIME],statinfo[ST_SIZE],'xxx']
  #            env[fn] = data
    print '\n'
    return env

def readfilenamesfromfile(filename):
  files = set()
  f = open(filename, 'r')

  fixpath = re.compile('\\\\')
  leadingslash = re.compile('^%s' % fixpath.sub('/',epocroot()))
  newline = re.compile('\n')
  epoc32 = re.compile('^epoc32');
  trailingtab = re.compile('\t\d+') #normally in rombuild files...
  for line in f:
    line = newline.sub('',line)
    name = string.lower(leadingslash.sub('',fixpath.sub('/',line)))
    if(epoc32.search(name)):
      name = trailingtab.sub('',name) 
      files.add(name)
  f.close()  
  return files

