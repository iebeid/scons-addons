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

import os, sys, string, copy
import SCons.Environment
import SCons.Platform
import SCons
from Util import GetPlatform
default_funcs = []

class EnvironmentBuilder(object):
   """ Builder class for scons environments.
       Used to build up an environment based on user settings.
   """
   # Level options
   NONE = 0
   MINIMAL = 1
   STANDARD = 2
   EXTENSIVE = 3
   MAXIMUM = 4
   
   # Opt flags
   REDUCE_SIZE = 'reduce_size'
   FAST_MATH = 'fast_math'
   ARCH_SPEC = 'arch_specific'
   
   # Warning flags
   WARN_AS_ERROR = 'warn_as_error'
   WARN_STRICT   = 'warn_strict'

   
   def __init__(self):
      """ Initialize the class with defaults. """
      global default_funcs
      self.debugLevel   = EnvironmentBuilder.NONE 
      self.debugTags    = []
      self.optLevel     = EnvironmentBuilder.NONE
      self.optTags      = []
      self.warningLevel = EnvironmentBuilder.MINIMAL 
      self.warningTags  = []
      self.profEnabled  = False
      self.exceptionsEnabled = False

      # List of [ [compilers], [platforms], func ]
      # If compiler or platform list is empty, then ignore that check
      self.funcList     = copy.copy(default_funcs)

   def buildEnvironment(self, **kw):
      """ Build an environment object and apply any options to it.
          Takes same parameters as Environment() in SCons.
      """
      new_env = apply(SCons.Environment.Environment, [], kw)
      self.applyOptionsToEnvironment(new_env)
      return new_env

   def enableDebug(self, level=STANDARD, tags=[]):
      self.debugLevel = level
      self.debugTags = tags
   def disableDebug(self):
      self.enableDebug(level=NONE)
      
   def enableOpt(self, level=STANDARD, tags=[]):
      self.optLevel = level
      self.optTags = tags
   def disableOpt(self):
      self.enableOpt(NONE)
      
   def enableProfiling(self, val=True):
      self.profEnabled = val
   def disableProfiling(self):
      self.enableProfiling(False)
   
   def enableWarnings(self, level=STANDARD, tags=[]):
      self.warningLevel = level
      self.warningTags = tags
   def disableWarnings(self):
      self.enableWarnings(NONE)
   
   def enableExceptions(self, val=True):
      self.exceptionsEnabled = val
   def disableExceptions(self):
      self.enableExceptions(False)

   # ---- Option application ---- #
   def applyOptionsToEnvironment(self, env):
      tools = env["TOOLS"]
      print "Using tools: ", tools
      
      # Find the compilers/builders we are using
      c_compiler = env["CC"]
      cxx_compiler = env["CXX"]
      linker = env["LINK"]
      # one of: ['cygwin','irix','sunos','linux','freebsd','darwin','win32']
      platform = GetPlatform()
      
      # Based on compiler and platform
      for f in self.funcList:
         (compiler_list,platform_list, func) = f
         if (len(compiler_list)==0) or (c_compiler in compiler_list) or (cxx_compiler in compiler_list):
            if (len(platform_list)==0) or (platform in platform_list):
               func(self, env)


# ----------- Option appliers ------------ #
# ---- GCC ---- #
def gcc_optimizations(bldr, env):
   if EnvironmentBuilder.NONE == bldr.optLevel:
      return
   
   CCFLAGS = []
   CXXFLAGS = []
   CPPDEFINES = []

   if EnvironmentBuilder.REDUCE_SIZE in bldr.optTags:
      CCFLAGS.append('-Os')
   else:
      if bldr.optLevel == EnvironmentBuilder.MINIMAL:
         CCFLAGS.append('-O1')
      elif bld.optLevel == EnvironmentBuilder.STANDARD:
         CCFLAGS.append('-O2')
      elif ((bld.optLevel == EnvironmentBuilder.EXTENSIVE) or
            (bld.optLevel == EnvironmentBuilder.MAXIMUM)):
         CCFLAGS.append('-O3')

   # Fast math
   if EnvironmentBuilder.FAST_MATH in bldr.optTags:
      CCFLAGS.append('-ffast-math')
   
   # TODO: Do architecture specific optimizations here
   env.Append(CXXFLAGS=CXXFLAGS, CCFLAGS=CCFLAGS, CPPDEFINES=CPPDEFINES)

def gcc_debug(bldr, env):
   print "Calling gcc_debug."
   if EnvironmentBuilder.NONE == bldr.debugLevel:
      return
   env.Append(CCFLAGS="-g")

def gcc_warnings(bldr, env):
   CCFLAGS = []
   
   if EnvironmentBuilder.NONE == bldr.warningLevel:
      CCFLAGS.append('-w')
   if bldr.warningLevel == EnvironmentBuilder.MINIMAL:
      pass
   elif bldr.warningLevel == EnvironmentBuilder.STANDARD:
      CCFLAGS.append('-Wall')
   elif bldr.warningLevel == EnvironmentBuilder.EXTENSIVE:
      CCFLAGS.append(['-Wall','-Wextra'])
   elif bldr.warningLevel == EnvironmentBuilder.MAXIMUM:
      CCFLAGS.extend(['-Wall','-Wextra'])

   # warnings as errors
   if EnvironmentBuilder.WARN_AS_ERROR in bldr.debugTags:
      CCFLAGS.append('-Werror')
   
   if EnvironmentBuilder.WARN_STRICT in bldr.debugTags:
      CCFLAGS.append('-pedantic')
      
   env.Append(CCFLAGS=CCFLAGS)
   
def gcc_misc(bldr, env):
   if bldr.profEnabled:
      env.Append(CCFLAGS="-pg", LINKFLAGS='-pg')   

# GCC functions
default_funcs.append([['gcc','g++'],[],gcc_optimizations])
default_funcs.append([['gcc','g++'],[],gcc_debug])
default_funcs.append([['gcc','g++'],[],gcc_warnings])


# ---- DEFAULT ---- #
def default_debug_define(bldr,env):
   if EnvironmentBuilder.NONE != bldr.optLevel and EnvironmentBuilder.NONE == bldr.debugLevel:
      env.Append(CPPDEFINES="NDEBUG")
   elif EnvironmentBuilder.NONE == bldr.optLevel and EnvironmentBuilder.NONE != bldr.debugLevel:
      env.Append(CPPDEFINES="_DEBUG")

default_funcs.append([[],[],default_debug_define])
