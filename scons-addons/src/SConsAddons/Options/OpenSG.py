"""SConsAddons.Options.OpenSG

Defines options for OpenSG project
"""

#
# __COPYRIGHT__
#
# This file is part of scons-addons.
#
# Scons-addons is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Scons-addons is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with scons-addons; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

__revision__ = "__FILE__ __REVISION__ __DATE__ __DEVELOPER__"

import SCons.Environment;   # Get the environment crap
import SCons;
import SConsAddons.Options;   # Get the modular options stuff
import SCons.Util
import sys;
import os;
import re;
import string;

from SCons.Util import WhereIs
pj = os.path.join;


class OpenSG(SConsAddons.Options.LocalUpdateOption):
   """ 
   Options object for capturing vapor options and dependencies.
   """

   def __init__(self, name, requiredVersion, required=True):
      """
         name - The name to use for this option
         requiredVersion - The version of vapor required (ex: "0.16.7")
         required - Is the dependency required?  (if so we exit on errors)
      """
      help_text = """Base directory for OpenSG. (bin should be under this directory for osg-config).""";
      self.baseDirKey = "OpenSGBaseDir";
      self.requiredVersion = requiredVersion;
      self.required = required;
      SConsAddons.Options.LocalUpdateOption.__init__(self, name, self.baseDirKey, help_text);
      
      # configurable options
      self.baseDir = None;
      self.osgconfig_cmd = None;

      # Settings to use
      self.found_libs = None;
      self.found_cflags = None;
      self.found_lib_paths = None;
      self.found_defines = None;
      
   def checkRequired(self, msg):
      """ Called when there is config problem.  If required, then exit with error message """
      print msg;
      if self.required:
         sys.exit(1);

   def startUpdate(self):
      print "Checking for OpenSG...",
      
   def setInitial(self, optDict):
      " Set initial values from given dict "
      if self.verbose:
         print "   Setting initial OpenSG settings."
      if optDict.has_key(self.baseDirKey):
         self.baseDir = optDict[self.baseDirKey];
         self.osgconfig_cmd = pj(self.baseDir, 'bin', 'osg-config')
         if self.verbose:
            print "   %s specified or cached. [%s]."% (self.baseDirKey, self.baseDir);
        
   def find(self, env):
      # Quick exit if nothing to find
      if self.baseDir != None:
         return;
      
      # Find osg-config and call it to get the other arguments
      sys.stdout.write("searching for osg-config...\n");
      self.osgconfig_cmd = WhereIs('osg-config');
      if not self.osgconfig_cmd:
         self.checkRequired("   could not find osg-config.");
         return
      else:
         sys.stdout.write("   found osg-config.\n");
         found_ver_str = os.popen(self.osgconfig_cmd + " --version").read().strip();
         sys.stdout.write("   version:%s"%found_ver_str);
         
         # find base dir
         self.baseDir = os.popen(self.osgconfig_cmd + " --prefix").read().strip();
         if not os.path.isdir(self.baseDir):
            self.checkRequired("   returned directory does not exist:%s"% self.baseDir);
            self.baseDir = None;
         else:
            print "   found at: ", self.baseDir;
   
   def convert(self):
      pass;
   
   def set(self, env):
      if self.baseDir:
         env[self.baseDirKey] = self.baseDir;
   
   def validate(self, env):
      # Check that path exist
      # Check that osg-config exist
      # Check that an include file: include/OpenSG/OSGConfig.h  exists
      # Update the temps for later usage
      passed = True;
      if not os.path.isdir(self.baseDir):
         self.checkRequired("OpenSG base dir does not exist:%s"%self.baseDir);
         return
      if not os.path.isfile(self.osgconfig_cmd):
         self.checkRequired("osg-config does not exist:%s"%self.osgconfig_cmd);
         return
         
      # Check version requirement
      found_ver_str = os.popen(self.osgconfig_cmd + " --version").read().strip();
      req_ver = self.requiredVersion.split(".")
      found_ver = found_ver_str.split(".");
      if found_ver < req_ver:
         passed = False;
         self.checkRequired("   found version is to old: required:%s found:%s"%(self.requiredVersion,found_ver_str));
         
      osgconfig_file = pj(self.baseDir, 'include', 'OpenSG', 'OSGConfig.h');
      if not os.path.isfile(osgconfig_file):
         self.checkRequired("OSGConfig.h not found:%s"%osgconfig_file);
         return
         
      # If not pass, then clear everything
      # Else we pass, set up the real data structures to use (initialized in constructor)      
      if not passed:
         # Clear everything
         self.baseDir = None;
         self.vprconfig_cmd = None;
         edict = env.Dictionary();
         if edict.has_key(self.baseDirKey):
            del edict[self.baseDirKey];
      else:
         # Get output from osg-config
         # Res that when matched against osg-config output should match the options we want
         # In future could try to use INCPREFIX and other platform neutral stuff
         inc_re = re.compile(r'(?: |^)-I(\S*)', re.MULTILINE);
         lib_re = re.compile(r'(?: |^)-l(\S*)', re.MULTILINE);
         lib_path_re = re.compile(r'(?: |^)-L(\S*)', re.MULTILINE);
         link_from_lib_re = re.compile(r'((?: |^)-[^lL]\S*)', re.MULTILINE);
         defines_re = re.compile(r'(?: |^)-D(\S*)', re.MULTILINE);
         
         # Returns lists of the options we want
         self.found_cflags = os.popen(self.osgconfig_cmd + " --cflags").read().strip().split(" ")
         self.found_libs = {}
         self.found_libs["base"] = lib_re.findall(os.popen(self.osgconfig_cmd + " --libs Base").read().strip());
         self.found_libs["system"] = lib_re.findall(os.popen(self.osgconfig_cmd + " --libs System").read().strip());
         self.found_libs["glut"] = lib_re.findall(os.popen(self.osgconfig_cmd + " --libs GLUT").read().strip());
         self.found_libs["x"] = lib_re.findall(os.popen(self.osgconfig_cmd + " --libs X").read().strip());
         self.found_libs["qt"] = lib_re.findall(os.popen(self.osgconfig_cmd + " --libs QT").read().strip());         
         self.found_lib_paths = {}
         self.found_lib_paths["base"] = lib_path_re.findall(os.popen(self.osgconfig_cmd + " --libs Base").read().strip());
         self.found_lib_paths["system"] = lib_path_re.findall(os.popen(self.osgconfig_cmd + " --libs System").read().strip());
         self.found_lib_paths["glut"] = lib_path_re.findall(os.popen(self.osgconfig_cmd + " --libs GLUT").read().strip());
         self.found_lib_paths["x"] = lib_path_re.findall(os.popen(self.osgconfig_cmd + " --libs X").read().strip());
         self.found_lib_paths["qt"] = lib_path_re.findall(os.popen(self.osgconfig_cmd + " --libs QT").read().strip());
         self.found_defines = defines_re.findall(os.popen(self.osgconfig_cmd + " --cflags").read().strip())
         
         print "[OK]"
             
   def updateEnv(self, env, lib="system"):
      """ Add environment options for building against vapor.
          lib: One of: base, system, glut, x, qt.
      """
      if self.found_cflags:
         env.Append(CXXFLAGS = self.found_cflags);
      if self.found_libs:
         if self.found_libs.has_key(lib):
            env.Append(LIBS = self.found_libs[lib]);
         else:
            print "ERROR: Could not find OpenSG libs for lib=", lib
      if self.found_lib_paths:
         if self.found_lib_paths.has_key(lib):
            env.Append(LIBPATH = self.found_lib_paths[lib]);
         else:
            print "ERROR: Could not find OpenSG lib paths for lib=", lib
         
   def dumpSettings(self):
      "Write out the settings"
      print "OpenSGBaseDir:", self.baseDir;
      print "osg-config:", self.osgconfig_cmd;      
      print "CXXFLAGS:", self.found_cflags;
      if self.found_libs:
         for lib_name in self.found_libs.keys():
            print "LIBS (%s):"%lib_name, self.found_libs[lib_name]
            print "LIBPATH (%s):"%lib_name, self.found_lib_paths[lib_name]
      print "DEFINES:", self.found_defines

