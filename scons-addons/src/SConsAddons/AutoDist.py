############################################################## autodist-cpr beg
#
# AutoDist - Automatic distribution builder and packager for
#            SCons-based builds
# AutoDist is (C) Copyright 2002 by Ben Scott
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# -----------------------------------------------------------------
# File:          $RCSfile$
# Date modified: $Date$
# Version:       $Revision$
# -----------------------------------------------------------------
############################################################## autodist-cpr end

from os import path

import SCons.Defaults
import SCons.Environment
import SCons.Node.FS

# SCons shorthand mappings
Environment    = SCons.Environment.Environment
File           = SCons.Node.FS.default_fs.File
Program        = SCons.Defaults.Program
SharedLibrary  = SCons.Defaults.SharedLibrary
StaticLibrary  = SCons.Defaults.StaticLibrary

# The currently defined prefix
_prefix = '/usr/local'

# Returns the current installation prefix. If an argument is supplied, the
# prefix is changed to the supplied value and then returned.
def Prefix(prefix = None):
   global _prefix

   # Change the prefix if requested
   if prefix != None:
      _prefix = prefix

   # Return the current prefix
   return _prefix


class Assembly:
   def __init__(self, name):
      self.data = {}
      self.data['name']     = name
      self.data['sources']  = []
      self.data['includes'] = []
      self.data['libs']     = []
      self.data['libpaths'] = []

   def addSources(self, sources):
      # Use File() to figure out the absolute path to the file
      srcs = map(File, sources)
      # Add these sources into the mix
      self.data['sources'].extend(srcs)

   def addLibs(self, libs):
      self.data['libs'].extend(libs)

   def addLibPaths(self, libpaths):
      self.data['libpaths'].extend(libpaths)


class Library(Assembly):
   def __init__(self, name, shared = 0):
      Assembly.__init__(self, name)
      self.data['shared'] = shared

   def build(self, env):
      if self.data['shared']:
         makeLib = env.SharedLibrary
      else:
         makeLib = env.StaticLibrary

      # Build rule
      lib = makeLib(self.data['name'], self.data['sources'])

      # Install rule
      env.Install(path.join(Prefix(), 'lib'), lib)

class Program(Assembly):
   def __init__(self, name):
      Assembly.__init__(self, name)

   def build(self, env = None):
      # Build rule
      prog = env.Program(self.data['name'], source  = self.data['sources'])

      # Install rule
      env.Install(path.join(Prefix(), 'bin'), prog)

class Package:
   data = {}

   def __init__(self, name, version):
      self.data = {
         'name'         : name,
         'assemblies'   : [],
         'extra_dist'   : [],
      }

      # Extract the version parameters
      import re
      re_matches = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version)
      self.data['version_major'] = re_matches.group(1)
      self.data['version_minor'] = re_matches.group(2)
      self.data['version_patch'] = re_matches.group(3)

   def CreateLibrary(self, name, shared):
      lib = Library(name, shared)
      self.data['assemblies'].extend([lib])
      return lib

   def CreateProgram(self, name):
      prog = Program(name)
      self.data['assemblies'].extend([prog])
      return prog

   def addExtraDist(self, files):
      self.data['extra_dist'].extend(files)


   def build(self, baseEnv = None):
      # Clone the base environment if we have one
      if baseEnv:
         env = baseEnv.Copy()
      else:
         env = Environment()
      
      env.Alias('install', Prefix())
      for assembly in self.data['assemblies']:
         assembly.build(env)
