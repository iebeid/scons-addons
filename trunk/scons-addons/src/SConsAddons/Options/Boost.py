"""SConsAddons.Options.Boost

Definds options for boost project
"""

__revision__ = "__FILE__ __REVISION__ __DATE__ __DEVELOPER__"

#!python
# SCons based build file for Boost
# Base file
import SCons.Environment
import SCons
import SConsAddons.Options
from SConsAddons.Options import LocalUpdateOption
import SCons.Util

import string
import sys
import os
import re

pj = os.path.join

from SCons.Util import WhereIs

import SCons.SConf
Configure = SCons.SConf.SConf
# ##############################################
# Options
# ##############################################
class Boost(SConsAddons.Options.PackageOption):
   def __init__(self, name, requiredVersion, libs=[], required=True):
      """
         name - The name to use for this option
         requiredVersion - The version of Boost required (ex: "1.30.0")
         libs - Boost libraries needed that are actually compiled
         required - Is the dependency required?  (if so we exit on errors)
      """
      help_text = """Base directory for Boost. include, and lib should be under this directory"""
      self.baseDirKey = "BoostBaseDir"
      self.requiredVersion = requiredVersion
      self.libs = map(lambda x: 'boost_'+x, libs)
      self.required = required
      LocalUpdateOption.__init__(self, name, self.baseDirKey, help_text)

      # configurable options
      self.baseDir = None
      self.boostHeader = None

   def checkRequired(self, msg):
      """ Called when there is config problem.  If required, then exit with error message """
      print msg
      if self.required:
         SCons.Script.SConscript.Exit()

   def isAvailable(self):
      return self.available

   def setInitial(self, optDict):
      " Set initial values from given dict "
      sys.stdout.write("checking for Boost...")
      if optDict.has_key(self.baseDirKey):
         self.baseDir = optDict[self.baseDirKey]
         self.boostHeader = pj(self.baseDir, 'include', 'boost', 'version.hpp')
         sys.stdout.write("specified or cached. [%s].\n"% self.baseDir)
         assert os.path.isfile(self.boostHeader), "boost/version.hpp does not exist"

   def find(self, env):
      # Quick exit if nothing to find
      if self.baseDir != None:
         return


      # Find boost/version.hpp
      sys.stdout.write("searching...\n")
      self.boostHeader = SCons.Script.SConscript.FindFile(pj('boost', 'version.hpp'),
                                    string.split(env['ENV']['CPLUS_INCLUDE_PATH'], os.pathsep))
      if None == self.boostHeader:
         self.checkRequired("   could not find boost/version.hpp.")
      else:
         self.boostHeader = str(self.boostHeader)
         sys.stdout.write("   found boost/version.hpp.\n")
         ver_file = file(self.boostHeader)
         found_ver_str = int(re.search("define\s+?BOOST_VERSION\s+?(\d*)", ver_file.read()).group(1))
         found_ver_str = str(found_ver_str / 100000) + '.' + str(found_ver_str / 100 % 1000) + '.' + str(found_ver_str % 100)
         sys.stdout.write("   version:%s"%found_ver_str)

         # find base dir
         self.baseDir = os.path.dirname(os.path.dirname(os.path.dirname(self.boostHeader)))
         if not os.path.isdir(self.baseDir):
            self.checkRequired("   returned directory does not exist:%s"% self.baseDir)
            self.baseDir = None
         else:
            print "   found at: ", self.baseDir

   def convert(self):
      pass

   def set(self, env):
      if self.baseDir:
         env[self.baseDirKey] = self.baseDir

   def validate(self, env):
      # Check that path exist
      # Check that an include file: boost/config.hpp  exists
      # Update the temps for later usage
      passed = True
      if not os.path.isdir(self.baseDir):
         passed = False
         self.checkRequired("boost base dir does not exist:%s"%self.baseDir)
      if not os.path.isfile(self.boostHeader):
         passed = False
         self.checkRequired("boost/thread.hpp does not exist:%s"%self.boostHeader)
      for lib in self.libs:
         static_lib = env.subst('${LIBPREFIX}%s${LIBSUFFIX}' % (lib))
         shared_lib = env.subst('${SHLIBPREFIX}%s${SHLIBSUFFIX}' % (lib))
         libdir = pj(self.baseDir, 'lib')
         if not os.path.isfile(pj(libdir, static_lib)) and not os.path.isfile(pj(libdir, shared_lib)):
            passed = False
            self.checkRequired('required library does not exist: %s' % (lib))

      # Check version requirement
      ver_file = file(self.boostHeader)
      found_ver_str = int(re.search("define\s+?BOOST_VERSION\s+?(\d*)", ver_file.read()).group(1))
      found_ver_str = str(found_ver_str / 100000) + '.' + str(found_ver_str / 100 % 1000) + '.' + str(found_ver_str % 100)
      req_ver = [int(n) for n in self.requiredVersion.split('.')]
      found_ver = [int(n) for n in found_ver_str.split('.')]
      if found_ver < req_ver:
         passed = False
         self.checkRequired("   found version is to old: required:%s found:%s"%(self.requiredVersion,found_ver_str))

      self.found_incs = None
      self.found_libs = None
      self.found_lib_paths = None
      self.found_link_from_libs = None

      if not passed:
         # Clear everything
         self.baseDir = None
         self.boostHeader= None
         edict = env.Dictionary()
         if edict.has_key(self.baseDirKey):
            del edict[self.baseDirKey]
      else:
         # Returns lists of the options we want
         self.found_incs = [pj(self.baseDir, 'include')]
         self.found_libs = self.libs
         self.found_lib_paths = [pj(self.baseDir, 'lib')]
         self.available = True

   def updateEnv(self, env):
      """ Add environment options for building against Boost.Thread"""
      if self.found_incs:
         env.Append(CPPPATH = self.found_incs)
      if self.found_libs:
         env.Append(LIBS = self.found_libs)
      if self.found_lib_paths:
         env.Append(LIBPATH = self.found_lib_paths)

   def dumpSettings(self):
      "WRite out the settings"
      print "BoostBaseDir:", self.baseDir
      print "CPPPATH:", self.found_incs
      print "LIBS:", self.found_libs
      print "LIBPATH:", self.found_lib_paths
