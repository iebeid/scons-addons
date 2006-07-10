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

import os, sys, string, copy, re
import SCons.Environment
import SCons.Platform
import SCons
import Options
from Util import GetPlatform, GetArch
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
   
   # MSVC runtime
   MSVC_MT_DLL_RT     = "msvc_mt_dll_rt"
   MSVC_MT_DBG_DLL_RT = "msvc_mt_dbg_dll_rt"
   MSVC_MT_RT         = "msvc_mt_rt"
   MSVC_MT_DBG_RT     = "msvc_mt_dbg_rt"
   
   # CPU ARCH
   AUTODETECT_ARCH    = "autodetect_arch"
   IA32_ARCH          = "ia32_arch"
   X64_ARCH           = "x64_arch"
   IA64_ARCH          = "ia64_arch"
   PPC_ARCH           = "ppc_arch"
   PPC64_ARCH         = "ppc64_arch"

   
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
      self.exceptionsEnabled = True
      self.rttiEnabled  = True            
      self.cpuArch      = None
      
      # Darwin specific
      self.darwinUniversalEnabled = False
      self.darwinSdk = ''
      
      # MSVC specific
      self.msvcRuntime  = None
      
      # List of [ [compilers], [platforms], func ]
      # If compiler or platform list is empty, then ignore that check
      self.funcList     = copy.copy(default_funcs)

   def buildEnvironment(self, options=None, variant=None, **kw):
      """ Build an environment object and apply any options to it.
          Takes same parameters as Environment() in SCons.
          options - If passed and is instance of SCons.Options.Options, it will
                    be applied to environment before builder apply's it's options.
          variant - If passed, it will be added as entry to environment
                    and available when applying options.
      """
      if options and not isinstance(options, Options.Options):
         kw["options"] = options      
      new_env = apply(SCons.Environment.Environment, [], kw)      
      self.applyToEnvironment(new_env,variant, options)
      return new_env
   
   def applyToEnvironment(self, env, variant=None, options=None):
      """ Apply current builder options to an existing environment.
          Returns env argument. 
         
         Ex: new_env = bldr.applyToEnvironment(env.Copy())
      """
      if variant:
         env["variant"] = variant
      if options and isinstance(options, Options.Options):
         options.Apply(env)
      self._applyOptionsToEnvironment(env)
      return env

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
      
   def enableRTTI(self, val=True):
      self.rttiEnabled = val
   def disableRTTI(self):
      self.enableRTTI(False)
      
   def setCpuArch(self, val=AUTODETECT_ARCH):
      if val != EnvironmentBuilder.AUTODETECT_ARCH:
         self.cpuArch = val
      else:
         arch_map = {"ia32":EnvironmentBuilder.IA32_ARCH,
                     "x86_64":EnvironmentBuilder.X64_ARCH,
                     "ppc":EnvironmentBuilder.PPC_ARCH,
                     "ppc64":EnvironmentBuilder.PPC64_ARCH}
         self.cpuArch = arch_map.get(GetArch(), EnvironmentBuilder.AUTODETECT_ARCH)

   # ---- Darwin specific ----- #
   def darwin_enableUniversalBinaries(self, val=True):
      self.darwinUniversalEnabled = val
   def darwin_disableUniversalBinaries(self):
      self.darwin_enableUniversalBinaries(False)

   def darwin_setSdk(self, val):
      self.darwinSdk = val
      
   # ---- MSVC specific ---- #
   def setMsvcRuntime(self, val):
      self.msvcRuntime = val
   
   # ---- Option application ---- #
   def _applyOptionsToEnvironment(self, env):
      tools = env["TOOLS"]
      #print "Using tools: ", tools
      
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
      elif bldr.optLevel == EnvironmentBuilder.STANDARD:
         CCFLAGS.append('-O2')
      elif ((bldr.optLevel == EnvironmentBuilder.EXTENSIVE) or
            (bldr.optLevel == EnvironmentBuilder.MAXIMUM)):
         CCFLAGS.append('-O3')

   # Fast math
   if EnvironmentBuilder.FAST_MATH in bldr.optTags:
      CCFLAGS.append('-ffast-math')
   
   # TODO: Do architecture specific optimizations here
   env.Append(CXXFLAGS=CXXFLAGS, CCFLAGS=CCFLAGS, CPPDEFINES=CPPDEFINES)

def gcc_debug(bldr, env):
   #print "Calling gcc_debug."
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

def gcc_linux_misc(bldr, env):
   assert isinstance(bldr, EnvironmentBuilder)
   if bldr.cpuArch:
      if bldr.cpuArch == EnvironmentBuilder.IA32_ARCH:
         env.Append(CXXFLAGS = ['-m32'],
                    LINKFLAGS = ['-m32'])
      elif bldr.cpuArch == EnvironmentBuilder.X64_ARCH:
         env.Append(CXXFLAGS = ['-m64'],
                    LINKFLAGS = ['-m64'])

def gcc_darwin_misc(bldr,env):
   assert isinstance(bldr, EnvironmentBuilder)

   if bldr.darwinUniversalEnabled:
      env.Append(CXXFLAGS = ['-arch', 'ppc', '-arch', 'i386', '-arch', 'ppc64'],
                 LINKFLAGS = ['-arch', 'ppc', '-arch', 'i386', '-arch', 'ppc64'])
   else:
      if bldr.cpuArch != None:
         if bldr.cpuArch == EnvironmentBuilder.IA32_ARCH:
            env.Append(CXXFLAGS = ['-arch', 'i386'],
                       LINKFLAGS = ['-arch', 'i386'])
         elif bldr.cpuArch == EnvironmentBuilder.PPC_ARCH:
            env.Append(CXXFLAGS = ['-arch', 'ppc'],
                       LINKFLAGS = ['-arch', 'ppc'])
         elif bldr.cpuArch == EnvironmentBuilder.PPC64_ARCH:
            env.Append(CXXFLAGS = ['-arch', 'ppc64'],
                       LINKFLAGS = ['-arch', 'ppc64'])

   if bldr.darwinSdk != '':
      env.Append(CXXFLAGS = ['-isysroot', bldr.darwinSdk],
                 LINKFLAGS = ['-isysroot', bldr.darwinSdk])

      sdk_re = re.compile('MacOSX(10\..*?)u?\.sdk')
      match = sdk_re.search(bldr.darwinSdk)
      if match is not None:
         min_osx_ver = '-mmacosx-version-min=' + match.group(1)
         env.Append(CXXFLAGS = [min_osx_ver], LINKFLAGS = [min_osx_ver])

# GCC functions
default_funcs.append([['gcc','g++'],[],gcc_optimizations])
default_funcs.append([['gcc','g++'],[],gcc_debug])
default_funcs.append([['gcc','g++'],[],gcc_warnings])
default_funcs.append([['gcc','g++'],[],gcc_misc])
default_funcs.append([['gcc','g++'],['linux'],gcc_linux_misc])
default_funcs.append([['gcc','g++'],['mac'],gcc_darwin_misc])

# ---- MSVC ---- #      
def msvc_optimizations(bldr, env):
   if EnvironmentBuilder.NONE == bldr.optLevel:
      return
   
   CCFLAGS = []
   CXXFLAGS = []
   CPPDEFINES = []
   LINKFLAGS = ["/RELEASE",]

   if EnvironmentBuilder.REDUCE_SIZE in bldr.optTags:
      CCFLAGS.extend(['/O1'])
   else:
      if bldr.optLevel == EnvironmentBuilder.MINIMAL:
         CCFLAGS.extend(['/Ot','/Og'])
      elif bldr.optLevel == EnvironmentBuilder.STANDARD:
         CCFLAGS.append('/O2')
      elif ((bldr.optLevel == EnvironmentBuilder.EXTENSIVE) or
            (bldr.optLevel == EnvironmentBuilder.MAXIMUM)):
         CCFLAGS.append('/Ox')

   # Fast math
   if EnvironmentBuilder.FAST_MATH in bldr.optTags:
      CCFLAGS.append('/fp:fast')
   
   # TODO: Do architecture specific optimizations here
   # /arch:SSE/SEE2 /G1 /G2 
   # /favor
   env.Append(CXXFLAGS=CXXFLAGS, CCFLAGS=CCFLAGS, CPPDEFINES=CPPDEFINES, LINKFLAGS=LINKFLAGS)

def msvc_debug(bldr, env):
   """ TODO: Update to handle PDB debug database files. 
       TODO: Add support for run-time error checking.
   """
   print "Calling gcc_debug."
   if EnvironmentBuilder.NONE == bldr.debugLevel:
      return
   env.Append(CCFLAGS=['/Od','/Ob0','/Z7'],
              LINKFLAGS=['/DEBUG'])

def msvc_warnings(bldr, env):
   CCFLAGS = []
   
   if EnvironmentBuilder.NONE == bldr.warningLevel:
      CCFLAGS.append('/W0')
   if bldr.warningLevel == EnvironmentBuilder.MINIMAL:
      CCFLAGS.append('/W1')
   elif bldr.warningLevel == EnvironmentBuilder.STANDARD:
      CCFLAGS.append('/W2')
   elif bldr.warningLevel == EnvironmentBuilder.EXTENSIVE:
      CCFLAGS.append('/W3')
   elif bldr.warningLevel == EnvironmentBuilder.MAXIMUM:
      CCFLAGS.append('/Wall')

   # warnings as errors
   if EnvironmentBuilder.WARN_AS_ERROR in bldr.debugTags:
      CCFLAGS.append('/WX')
   
   if EnvironmentBuilder.WARN_STRICT in bldr.debugTags:
      CCFLAGS.append('/Za')
      
   env.Append(CCFLAGS=CCFLAGS)
   
def msvc_misc(bldr, env):
   # Runtime library
   rt_map = { EnvironmentBuilder.MSVC_MT_DLL_RT:'/MD',
              EnvironmentBuilder.MSVC_MT_DBG_DLL_RT:'/MDd',
              EnvironmentBuilder.MSVC_MT_RT:'/MT',
              EnvironmentBuilder.MSVC_MT_DBG_RT:'/MTd'
            }   
   if rt_map.has_key(bldr.msvcRuntime):
      env.Append(CCFLAGS=rt_map[bldr.msvcRuntime])

   # Exception handling
   if bldr.exceptionsEnabled:
      if env["MSVS"]["VERSION"] >= "7.1":
         env.Append(CCFLAGS='/EHsc')
      else:
         env.Append(CCFLAGS='/GX')

   # RTTI
   if bldr.rttiEnabled:
      env.Append(CCFLAGS="/GR")
      
   # Default defines
   env.Append(CPPDEFINES=["WIN32","_WINDOWS"])

# MSVC functions
default_funcs.append([['cl'],[],msvc_optimizations])
default_funcs.append([['cl'],[],msvc_debug])
default_funcs.append([['cl'],[],msvc_warnings])
default_funcs.append([['cl'],[],msvc_misc])

# ---- DEFAULT ---- #
def default_debug_define(bldr,env):
   if EnvironmentBuilder.NONE != bldr.optLevel and EnvironmentBuilder.NONE == bldr.debugLevel:
      env.Append(CPPDEFINES="NDEBUG")
   elif EnvironmentBuilder.NONE == bldr.optLevel and EnvironmentBuilder.NONE != bldr.debugLevel:
      env.Append(CPPDEFINES="_DEBUG")

default_funcs.append([[],[],default_debug_define])