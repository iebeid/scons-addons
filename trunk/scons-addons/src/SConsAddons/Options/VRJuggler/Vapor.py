"""SConsAddons.Options.VRJuggler.Vapor

Defines options for Vapor project
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


class Vapor(SConsAddons.Options.LocalUpdateOption):
   """ 
   Options object for capturing vapor options and dependencies.
   """

   def __init__(self, name, requiredVersion, required=True):
      """
         name - The name to use for this option
         requiredVersion - The version of vapor required (ex: "0.16.7")
         required - Is the dependency required?  (if so we exit on errors)
      """
      help_text = """Base directory for vapor. bin, include, and lib should be under this directory""";
      self.baseDirKey = "VprBaseDir";
      self.requiredVersion = requiredVersion;
      self.required = required;
      SConsAddons.Options.LocalUpdateOption.__init__(self, name, self.baseDirKey, help_text);
      
      # configurable options
      self.baseDir = None;
      self.vprconfig_cmd = None;
      
   def checkRequired(self, msg):
      """ Called when there is config problem.  If required, then exit with error message """
      print msg;
      if self.required:
         Exit();
      
   def setInitial(self, optDict):
      " Set initial values from given dict "
      sys.stdout.write("checking for vapor...");
      if optDict.has_key(self.baseDirKey):
         self.baseDir = optDict[self.baseDirKey];
         self.vprconfig_cmd = pj(self.baseDir, 'bin', 'vpr-config')
         sys.stdout.write("specified or cached. [%s].\n"% self.baseDir);
         assert os.path.isfile(self.vprconfig_cmd), "vpr-config does not exist"
        
   def find(self, env):
      # Quick exit if nothing to find
      if self.baseDir != None:
         return;
      
      # Find vpr-config and call it to get the other arguments
      sys.stdout.write("searching...\n");
      self.vprconfig_cmd = WhereIs('vpr-config');
      if None == self.vprconfig_cmd:
         self.checkRequired("   could not find vpr-config.");
      else:
         sys.stdout.write("   found vpr-config.\n");
         found_ver_str = os.popen(self.vprconfig_cmd + " --version").read().strip();
         sys.stdout.write("   version:%s"%found_ver_str);
         
         # find base dir
         self.baseDir = os.popen(self.vprconfig_cmd + " --prefix").read().strip();
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
      # Check that vpr-config exist
      # Check that an include file: include/vpr/vprConfig.h  exists
      # Update the temps for later usage
      passed = True;
      if not os.path.isdir(self.baseDir):
         passed = False;
         self.checkRequired("vpr base dir does not exist:%s"%self.baseDir);
      if not os.path.isfile(self.vprconfig_cmd):
         passed = False;
         self.checkRequired("vpr-config does not exist:%s"%self.vprconfig_cmd);
         
      # Check version requirement
      found_ver_str = os.popen(self.vprconfig_cmd + " --version").read().strip();
      req_ver = [int(n) for n in self.requiredVersion.split(".")];
      found_ver = [int(n) for n in found_ver_str.split(".")];
      if found_ver < req_ver:
         passed = False;
         self.checkRequired("   found version is to old: required:%s found:%s"%(self.requiredVersion,found_ver_str));
         
      vprconfig_file = pj(self.baseDir, 'include', 'vpr', 'vprConfig.h');
      if not os.path.isfile(vprconfig_file):
         passed = False;
         self.checkRequired("vprConfig.h not found:%s"%vprconfig_file);
         
      self.found_incs = None;
      self.found_libs = None;
      self.found_lib_paths = None;
      self.found_link_from_libs = None;
         
      if not passed:
         # Clear everything
         self.baseDir = None;
         self.vprconfig_cmd = None;
         edict = env.Dictionary();
         if edict.has_key(self.baseDirKey):
            del edict[self.baseDirKey];
      else:
         # Get output from vpr-config
         # Res that when matched against vpr-config output should match the options we want
         # In future could try to use INCPREFIX and other platform neutral stuff
         inc_re = re.compile(r'-I(\S*)', re.MULTILINE);
         lib_re = re.compile(r'-l(\S*)', re.MULTILINE);
         lib_path_re = re.compile(r'-L(\S*)', re.MULTILINE);
         link_from_lib_re = re.compile(r'(-[^lL]\S*)', re.MULTILINE);
         
         # Returns lists of the options we want
         self.found_incs = inc_re.findall(os.popen(self.vprconfig_cmd + " --includes").read().strip());
         self.found_libs = lib_re.findall(os.popen(self.vprconfig_cmd + " --libs --extra-libs").read().strip());
         self.found_lib_paths = lib_path_re.findall(os.popen(self.vprconfig_cmd + " --libs --extra-libs").read().strip());
         self.found_link_from_libs = link_from_lib_re.findall(os.popen(self.vprconfig_cmd + " --libs --extra-libs").read().strip());         
             
   def updateEnv(self, env):
      """ Add environment options for building against vapor"""
      if self.found_incs:
         env.Append(CPPPATH = self.found_incs);
      if self.found_libs:
         env.Append(LIBS = self.found_libs);
      if self.found_lib_paths:
         env.Append(LIBPATH = self.found_lib_paths);
      if self.found_link_from_libs:
         env.Append(LINKFLAGS = " ".join(self.found_link_from_libs));
         
   def dumpSettings(self):
      "Write out the settings"
      print "VprBaseDir:", self.baseDir;
      print "vpr-config:", self.vprconfig_cmd;
      print "CPPPATH:", self.found_incs;
      print "LIBS:", self.found_libs;
      print "LIBPATH:", self.found_lib_paths;
      print "LINKFLAGS:", self.found_link_from_libs;
