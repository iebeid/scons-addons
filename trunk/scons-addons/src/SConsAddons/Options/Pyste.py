"""SConsAddons.Options.Pyste

Defines option object for Pyste boost.python code generator.
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
import SCons.Util
import SConsAddons.Options;   # Get the modular options stuff
import SConsAddons.Util
import sys;
import os;
import re;
import string;

from SCons.Util import WhereIs
pj = os.path.join;

import SCons.Node.FS
import SCons.Scanner

#### SCANNER ######
def PysteScan(fs = SCons.Node.FS.default_fs):    
    """Return a prototype Scanner instance for scanning IDL source files"""
    ps = SCons.Scanner.Classic("PysteScan",
                               [".pyste",".Pyste"],
                               "CPPPATH",
                               """["'](\S*?\.h)["']""",
                               fs = fs)
    return ps
 
def PysteRecursiveScanFunction(node,env,path):
   """ Custom scanner that can handle recursive case when we need to 
       scan files that are not of the normal .pyste type """
   #print "PysteRecursive: Checking node: [%s] key:[%s] path:[%s]"%(str(node), node.scanner_key(), [str(f) for f in path])
   ps = PysteScan()
   scanner_key = node.scanner_key()
   if scanner_key in ps.skeys:
      return ps(node,env,path)
   else:
      other_scanner = env.get_scanner(scanner_key)
      return other_scanner(node,env,path)      
  
  

class Pyste(SConsAddons.Options.PackageOption):
   def __init__(self, name, requiredVersion, required=True):
      """
         name - The name to use for this option
         requiredVersion - The version of pyste required (ex: "0.9.26")
         required - Is the dependency required?  (if so we exit on errors)
      """
      help_text = """Full path to Pyste script.""";
      self.pysteScriptKey = "PysteScript";
      self.requiredVersion = requiredVersion;
      self.required = required;
      self.available = False
      SConsAddons.Options.LocalUpdateOption.__init__(self, name, self.pysteScriptKey, help_text);
      
      # Local helper options
      self.pysteScriptPath = None            # Full path to the script
      self.pysteScriptCommand = None         # Command for running the script
      
   def checkRequired(self, msg):
      """ Called when there is config problem.  If required, then exit with error message """
      print msg;
      if self.required:
         sys.exit(0);
         
   def isAvailable(self):
      return self.available
      
   def setInitial(self, optDict):
      " Set initial values from given dict "
      sys.stdout.write("loading pyste settings...");
      if optDict.has_key(self.pysteScriptKey):
         self.pysteScriptPath = optDict[self.pysteScriptKey];
         self.pysteScriptCommand = "python " + self.pysteScriptPath
         sys.stdout.write("   pyste specified or cached. [%s].\n"% self.pysteScriptPath);
        
   def find(self, env):
      # Only search for it if not specified already
      if self.pysteScriptPath == None:
         # Try to find it in path somehow
         print "   searching for pyste.py in path...";
         if(WhereIs('pyste.py') != None):
            self.pysteScriptPath = WhereIs('pyste.py')
            self.pysteScriptCommand = "python " + self.pysteScriptPath
            print "   found: %s" % self.pysteScriptPath
         else:
            self.checkRequired("   could not find pyste.py script.\n");
            return
 
      assert self.pysteScriptPath
      assert self.pysteScriptCommand
        
   def convert(self):
      pass;
   
   def set(self, env):
      if self.pysteScriptPath:
         env[self.pysteScriptKey] = self.pysteScriptPath;
   
   def validate(self, env):
      # Check that file exists
      # Check that vpr-config exist
      # Check version is correct
      # Check that an include file: include/vpr/vprConfig.h  exists
      # Update the temps for later usage
      passed = True
      if not self.pysteScriptPath:
          passed = False
      else:
          if not os.path.isfile(self.pysteScriptPath):
             passed = False;
             self.checkRequired("   pyste files does not exist:%s" % self.pysteScriptPath);

             # Check for version information
             print "   Checking version:",
             found_ver_str = os.popen(self.pysteScriptCommand + " --version").read().strip().split(" ")[-1];
             print found_ver_str
      
             # Check version requirement
             req_ver = [int(n) for n in self.requiredVersion.split(".")];
             found_ver = [int(n) for n in found_ver_str.split(".")];
             if found_ver < req_ver:
                 passed = False;
                 self.checkRequired("   found version is to old: required:%s found:%s"%(self.requiredVersion,found_ver_str));             
      
      # If we don't pass, then clear everything out
      if not passed:
         self.pysteScriptPath = None;
         self.pysteScriptCommand = None;
         self.available = False
      else:
         self.available = True
      
   def AddPysteBuilder(self,env):
       """ Add the builder and scanner for pyste to use. """
       def _path(env, dir, fs=SCons.Node.FS.default_fs):
           path = env["CPPPATH"]
           return tuple(fs.Rsearchall(SCons.Util.mapPaths(path, dir, env),
                                       clazz = SCons.Node.FS.Dir,
                                       must_exist = 0))
   
       pyste_scanner = SCons.Scanner.Base(function=PysteRecursiveScanFunction, 
                               name="PysteRecursive",
                               skeys=[".pyste",".Pyste"],
                               path_function=_path,
                               recursive=1)
       pyste_builder = SCons.Builder.Builder(action = "$PYSTE_CMD ${_concat('-I', CPPPATH, '', __env__)} --out=${TARGET} ${SOURCE}",
                               suffix=".cpp", src_suffix=".pyste",
                               );

       env.Append(BUILDERS = {'PysteModule' : pyste_builder})
       env.Append(SCANNERS = pyste_scanner)
             
   def updateEnv(self, env):
      """ Add pyste environment options, builder, and scanner."""
      if self.pysteScriptCommand:
         env.Append(PYSTE_CMD = self.pysteScriptCommand);
         self.AddPysteBuilder(env)
         
   def dumpSettings(self):
      "Write out the settings"
      print "Pyste option settings:"
      print "   PysteScript:", self.pysteScriptPath;
      print "   PysteCommand:", self.pysteScriptCommand;
      print "   Available:", self.available;
