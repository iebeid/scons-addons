"""
AutoDist

Automatic distribution builder and packager for SCons.

"""
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

__version__    = '0.2.1'
__author__     = 'Ben Scott and Allen Bierbaum'


import os
from os import path
import stat
import re

import SCons.Defaults
import SCons.Environment
import SCons.Node.FS
import SCons.Util
import types
import re
import time

pj = os.path.join


# SCons shorthand mappings
Action          = SCons.Action.Action
Builder         = SCons.Builder.Builder
Environment     = SCons.Environment.Environment
File            = SCons.Node.FS.default_fs.File
Value           = SCons.Node.Python.Value

config_script_contents = ""

class InstallableFile:
   """ Class to wrap any installable file.  ex. progs, libs, headers, docs, etc """
   def __init__(self, fileNode, prefix=""):
      self.fileNode = fileNode         # The scons node for the file
      self.prefix = prefix             # The prefix to use for the file (minus the package/bundle prefix)

   def __str__(self):
      """ an installable file's string representation is its prefix/name."""
      if prefix:
         return path.join(prefix, str(fileNode))
      else:
         return str(fileNode)

   def getFileNode(self):
      return self.fileNode

   def getPrefix(self):
      return self.prefix

   
class Header(InstallableFile):
   """ This class is meant to wrap a header file to install. """
   def __init__(self, fileNode, prefix=None):
      InstallableFile.__init__(self, fileNode, prefix)
      

class FileBundle:
   """ Wrapper class for a group of files to bundle together to install, archive, etc. 

       This class provides a method to hold a group of files together with their destination structure
       information.  Then it can be used to call install builders to setup an install where needed.
       
       One area of note is prefix handling.  To allow maximum flexibility there are several used prefixes.
       
       The file bundle has a prefix (this is relative to the package prefix).
       Each bundled file has a prefix (added when files is added).
       If path to the added file has a prefix it is added on as well.
       
       Final file location: passed_prefix/self.prefix/added.prefix/file_prefix/file_name
   """

   def __init__(self):
      """
      Construct file bundle object.
      """
      self.files = []                      # Installable files of class InstallableFile

   def addFiles(self, files, prefix = ""):
      """
      Add these files to the list of installable files.  They will be installed as:
      install.prefix/prefix/file_prefix. The list must come
      in as strings as they are processed through File().
      files - List of filenames (file nodes should also work)
      """
      for fn in files:                                     # For all files
         local_dir_prefix = ""
         if not isinstance(fn, SCons.Node.FS.Base):        # If we are a string filename, then get our local prefix
            local_dir_prefix = os.path.dirname(fn)
         f = InstallableFile( File(fn), pj(prefix, local_dir_prefix))   # Create new installable file
         self.files.append(f)                       # Append it on

   def getFiles(self):
      return self.files

   def buildInstall(self, env=None, prefix=""):
      """
      Calls install builder to setup the installation of the packaged files.
      Installs all files using the env environment under prefix.
      NOTE: file is installed into: prefix/added.prefix/file.prefix

      NOTE: Whatever the current directly is when this is called is the directory
      used for the builder command associated with this assembly.
      """
      
      # Clone the base environment if we have one
      if env:
         env = env.Copy()
      else:
         env = Environment()

      # Install the files from the bundle
      #print "FileBundle build Install:"
      for f in self.files:
         fnode = f.getFileNode()
         target_dir = path.join(prefix, f.getPrefix())
         #print "   file:[", str(fnode), " target dir: (", prefix, ", ", f.getPrefix(), ")" # target_dir
         env.Install(target_dir, fnode)        

# ############################################################################ #
#           ASSEMBLIES  
# ############################################################################ #      
class _Assembly:
   """ Base class for all assembly types that can be managed by a package. 
       This is an abstract type that provides common functionality and interface for all assemblies.
   """
   def __init__(self, pkg, baseEnv, prefix=""):
      """
      Constructs a new Assembly object with the given name within the given
      environment.
      """
      self.package = pkg                   # The package object we belong to
      self.built = False;                  # Flag set once we have been built
      self.installPrefix = prefix;         # Default install prefix

      # Clone the base environment if we have one
      if baseEnv:
         self.env = baseEnv.Copy()
      else:
         self.env = Environment()

   def setInstallPrefix(self, prefix):
      self.installPrefix = prefix

   def getInstallPrefix(self):
      return self.installPrefix
   
   def isBuilt(self):
      return self.built
   
   def build(self):
      """
      Sets up the build targets for this assembly.
      May only be called once.
      NOTE: Whatever the current directly is when this is called is the directory
      used for the builder command associated with this assembly.
      """      

      # Now actually do the build
      self._buildImpl()
      self.built = True;



class FileBundleAssembly(_Assembly):
   """ Wrapper class for a group of files to manage in an assembly for packaging. 

       One area of note is prefix handling.  To allow maximum flexibility there are several used prefixes.
       
       The file bundle has a prefix (this is relative to the package prefix).
       Each bundled file has a prefix (added when files is added).
       If path to the added file has a prefix it is added on as well.
       
       Final file location: package.prefix/self.prefix/added.prefix/file_prefix/file_name
   """

   def __init__(self, pkg, baseEnv, prefix=""):
      """
      Construct file bundle object.
      prefix - Prefix to install the files (relative to package)
      pkg - The package this bundle is a part of
      baseEnv - The environment that this bundle should be included in
      """
      _Assembly.__init__(self, pkg, baseEnv, prefix)

      self.files = []                      # Installable files of class InstallableFile
      self.built = False;                  # Flag set once we have been built      

   def addFiles(self, files, prefix = None):
      """
      Add these files to the list of installable files.  They will be installed as:
      package.prefix/self.prefix/prefix/file_prefix. The list must come
      in as strings as they are processed through File().
      files - List of filenames (file nodes should also work)
      """
      for fn in files:                                # For all filenames
         local_dir_prefix = ""
         if not isinstance(fn, SCons.Node.FS.Base):        # If we are a string filename, then get our local prefix
            local_dir_prefix = os.path.dirname(fn)
         f = InstallableFile( File(fn), pj(prefix, local_dir_prefix))   # Create new installable file
         self.files.append(f)                       # Append it on
         
   def getInstallableFiles(self):
      return self.files

   def isBuilt(self):
      return self.built;
   
   def build(self):
      """
      Sets up the build and install targets for this file bundle.
      May only be called once.
      NOTE: Whatever the current directly is when this is called is the directory
      used for the builder command associated with this assembly.
      """
      # Add files to the package file bundle
      fb = self.package.getFileBundle()

      for f in self.files:
         fnode = f.getFileNode()
         fb.addFiles([fnode], f.getPrefix())        

      self.built = True;         
      


class _CodeAssembly(_Assembly):
   """
   Base type for assemblys that are based on "code".

   This "abstract" class provides common functionality for Program,
   StaticLibrary, and SharedLibrary. You don't want to instantiate this class
   directly. It is meant to be private.
   """

   def __init__(self, filename, pkg, baseEnv, prefix=""):
      """
      Constructs a new Assembly object with the given name within the given
      environment.
      """
      _Assembly.__init__(self, pkg, baseEnv, prefix)
      
      self.fileNode      = File(filename)
      self.sources       = []
      self.includes      = []
      self.libs          = []
      self.libpaths      = []
      self.headers       = []

   def addSources(self, sources):
      """
      Adds the given list of source files into this assembly. The list must come
      in as strings as they are processed through File().
      """
      # Use File() to figure out the absolute path to the file
      srcs = map(File, sources)
      # Add these sources into the mix
      self.sources.extend(srcs)

   def addHeaders(self, headers, prefix = None):
      """
      Adds the given list of distribution header files into this assembly. These
      headers will be installed to self.package.prefix/include/prefix/file_prefix. The list must come
      in as strings as they are processed through File().
      """
      for fn in headers:                              # For all filenames in headers
         fn_dir = os.path.dirname(fn)                 # Find out if there is a local dir prefix
         hdr = Header( File(fn), pj(prefix,fn_dir))   # Create new header rep
         self.headers.append(hdr)                     # Append it on

   def addIncludes(self, includes):
      """
      Adds in the given list of include directories that this assembly will use
      while compiling.
      """
      self.includes.extend(includes)

   def addLibs(self, libs):
      """
      Adds in the given list of libraries directories that this assembly will
      link with.
      """
      self.libs.extend(libs)

   def addLibPaths(self, libpaths):
      """
      Adds in the given list of library directories that this assembly will use
      to find libraries while linking.
      """
      self.libpaths.extend(libpaths)

   def getHeaders(self):
      return self.headers

   def getSources(self):
      return self.sources

   def isBuilt(self):
      return self.built;
   
   def getFilename(self):
      return str(self.fileNode)
   
   def getAbsFilePath(self):
      return self.fileNode.get_abspath()

   def build(self):
      """
      Sets up the build and install targets for this assembly.
      May only be called once.
      NOTE: Whatever the current directly is when this is called is the directory
      used for the builder command associated with this assembly.
      """
      # Setup the environment for the build
      self.env.Append(CPPPATH = self.includes,
                      LIBPATH = self.libpaths,
                      LIBS    = self.libs)

      # Now actually do the build
      self._buildImpl()
      self.built = True;


class Library(_CodeAssembly):
   """
   This "abstract" class provides common functionality for StaticLibrary and
   SharedLibrary. You don't want to instantiate this class directly. It is
   meant to be private.
   """

   def __init__(self, libname, pkg, baseEnv, builderNames, installPrefix):
      """
      Creates a new library builder for a library of the given name.
      pkg - The package we are a part of
      baseEnv - The base environemnt to use
      builderNames - The names of the builders to use for building the libary: ex. 'SharedLibrary'
      installPrefix - Prefix (relative to the standard install path) to install this library
      """
      _CodeAssembly.__init__(self, libname, pkg, baseEnv, installPrefix)
      
      if type(builderNames) is types.StringType:
         self.builder_names = [ builderNames ]
      else:
         self.builder_names = builderNames      

   def _buildImpl(self):
      """
      Sets up the build dependencies and the install.
      """

      fb = self.package.getFileBundle()

      # Setup build and install for each built library
      # Use get_abspath() with fileNode so we get the path into the build_dir and not src dir
      # Only build libraries if we have sources
      if len(self.sources) > 0:
         for lib_builder in self.builder_names:
            lib_filepath = self.fileNode.get_abspath()
            lib = self.env.__dict__[lib_builder](lib_filepath, self.sources)

            # Lib to file bundle
            fb.addFiles([lib], self.installPrefix)

      # Install the headers in the source list
      for h in self.headers:
         headerNode = h.getFileNode()
         fb.addFiles([headerNode], pj('include', h.getPrefix()))
         
         #target = path.join(self.package.prefix, 'include', h.getPrefix())
         # Add on the prefix if this header has one
         #self.env.Install(target, headerNode)        


class SharedLibrary(Library):
   """ Sets up Library assembly with 'SharedLibrary' builder."""
   def __init__(self, libname, pkg, baseEnv = None, installPrefix='lib'):
      Library.__init__(self, libname, pkg, baseEnv, 'SharedLibrary', installPrefix)

class StaticLibrary(Library):
   """ Sets up Library assembly with 'StaticLibrary' builder """
   def __init__(self, libname, pkg, baseEnv = None, installPrefix='lib'):
      Library.__init__(self, libname, pkg, baseEnv, 'StaticLibrary', installPrefix)

class StaticAndSharedLibrary(Library):
   """ Sets up Library assembly with both 'StaticLibrary' and 'SharedLibrary' builders. """
   def __init__(self, libname, pkg, baseEnv = None, installPrefix='lib'):
      Library.__init__(self, libname, pkg, baseEnv, ['StaticLibrary', 'SharedLibrary'], installPrefix)


class Program(_CodeAssembly):
   """
   This object knows how to build (and install) an executable program from a
   given set of sources.
   """
   def __init__(self, progname, pkg, baseEnv = None, installPrefix='bin'):
      """
      Creates a new program builder for a program of the given name.
      """
      _CodeAssembly.__init__(self, progname, pkg, baseEnv, installPrefix)      

   def _buildImpl(self):
      """
      Sets up the build dependencies and the install.
      """
      # Build rule
      prog = self.env.Program(self.fileNode, source = self.sources)

      # Add executable to file bundle
      fb = self.package.getFileBundle()
      fb.addFiles([prog], self.installPrefix)
      
      # Install the binary
      #inst_prefix = self.package.prefix
      #if self.installPrefix:
      #   inst_prefix = pj(inst_prefix, self.installPrefix)
      #self.env.Install(inst_prefix, prog)

      
class Package:
   """
   A package defines a collection of distributables including programs and
   libraries. The Package class provides the ability to build, install, and
   package up distributions of your project.
   
   A package object provides an interface to add libraries, programs, headers,
   and support files to a single unit that can be installed.  It also shares
   an environment across all these different units to build.
   
   The package contains assemblies (objects that encapsulate things to build)
   and a FileBundle (which holds all the files that could be installed or handled).
   
   When assemblies are built, they should add any installable files to the package file bundle.
   """

   def __init__(self, name, version, prefix='/usr/local', baseEnv = None, description= None):
      """
      Creates a new package with the given name and version, where version is in
      the form of <major>.<minor>.<patch> (e.g 1.12.0)
      """
      self.name = name
      self.prefix = prefix
      self.assemblies = []
      self.fileBundle = FileBundle()                          # File bundle for all files
      self.extra_dist = []
      self.description = description
      if not self.description:
         self.description = self.name + " Package"
      
      if baseEnv:
         self.env = baseEnv.Copy()
      else:
         self.env = Environment()
         
      if type(version) is types.TupleType:
         (self.version_major, self.version_minor, self.version_patch) = version;
      else:
         re_matches = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version)
         self.version_major = int(re_matches.group(1))
         self.version_minor = int(re_matches.group(2))
         self.version_patch = int(re_matches.group(3))
         
   def getName(self):
      return self.name

   def getVersionMajor(self):
      return self.version_major

   def getVersionMinor(self):
      return self.version_minor

   def getVersionPatch(self):
      return self.version_patch
   
   def getFullVersion(self):
      return ".".join( (str(self.version_major), str(self.version_minor), str(self.version_patch)) )

   def getAssemblies(self):
      return self.assemblies

   def getExtraDist(self):
      return self.extra_dist
   
   def getFileBundle(self):
      return self.fileBundle

   # ###### Assembly factory methods ####### #
   def createSharedLibrary(self, name, baseEnv = None, installPrefix='lib'):
      """
      Creates a new shared library of the given name as a part of this package.
      The library will be built within the given environment.
      """
      if not baseEnv:
         baseEnv = self.env
      lib = SharedLibrary(name, self, baseEnv, installPrefix)
      self.assemblies.append(lib)
      return lib

   def createStaticLibrary(self, name, baseEnv = None, installPrefix='lib'):
      """
      Creates a new static library of the given name as a part of this package.
      The library will be built within the given environment.
      """
      if not baseEnv:
         baseEnv = self.env
      lib = StaticLibrary(name, self, baseEnv, installPrefix)
      self.assemblies.append(lib)
      return lib
   
   def createStaticAndSharedLibrary(self, name, baseEnv = None, installPrefix='lib'):
      """
      Creates new static and shared library of the given name as a part of this package.
      The library will be built within the given environment.
      """
      if not baseEnv:
         baseEnv = self.env
      lib = StaticAndSharedLibrary(name, self, baseEnv, installPrefix)
      self.assemblies.append(lib)
      return lib

   def createProgram(self, name, baseEnv = None, installPrefix='bin'):
      """
      Creates a new executable program of the given name as a part of this
      package. The program will be built within the given environment.
      """
      if not baseEnv:
         baseEnv = self.env
      prog = Program(name, self, baseEnv, installPrefix)
      self.assemblies.append(prog)
      return prog
   
   def createFileBundleAssembly(self, prefix, baseEnv = None): 
      """ Creates a new FileBundle object as part of this package. """
      bundle = FileBundleAssembly(pkg = self, baseEnv = baseEnv, prefix=prefix)
      self.assemblies.append(bundle)
      return bundle
   
   def createConfigAction(self, target, source, env):
      """ Called as action of config script builder """
      global config_script_contents
      
      new_contents = config_script_contents
      value_dict = source[0].value                  # Get dictionary from the value node
      
      all_lib_names = [os.path.basename(l.getAbsFilePath()) for l in self.assemblies if isinstance(l,Library)]
      lib_names = []
      for l in all_lib_names:
         if not lib_names.count(l):
            lib_names.append(l)
      inc_paths = [pj(self.prefix,'include'),]
      cflags = " ".join(["-I"+p for p in inc_paths])
      if value_dict["extraCflags"] != None:
         cflags = cflags + " " + value_dict["extraCflags"]
      lib_paths = [pj(self.prefix,'lib'),]
      
      # Extend varDict with local settings
      varDict = {}
      if value_dict["varDict"] != None:
         varDict = value_dict["varDict"]
         
      varDict["Libs"] = " ".join(["-L"+l for l in lib_paths]) + " " + " ".join(["-l"+l for l in lib_names])
      varDict["Cflags"] = cflags
      varDict["Version"] = self.getFullVersion()
      varDict["Name"] = self.name
      varDict["Description"] = self.description
      
      # Create the new content
      txt = "# config script generated for %s at %s\n" % (self.name, time.asctime())
      txt = txt + '# values: %s\n'%(source[0].get_contents(),)
      
      for k,v in value_dict["varDict"].items():
         if SCons.Util.is_String(v):
            txt = txt + 'vars["%s"] = "%s"\n' % (k,v)
         else:
            txt = txt + 'vars["%s"] = %s\n' % (k,v)            
            
      # Find and replace the replacable content
      cut_re = re.compile(r'(?<=# -- BEGIN CUT --\n).*?(?=# -- END CUT --)', re.DOTALL)
      new_contents = cut_re.sub(txt,config_script_contents)
      
      # Create and write out the new file (setting it executable)
      fname = str(target[0])
      f = open(str(target[0]), 'w')
      f.write(new_contents)
      f.close()
      os.chmod(fname, stat.S_IREAD|stat.S_IEXEC|stat.S_IWUSR)    # Set the file options
      
      return 0   # Successful build
      
   def createConfigScript(self, name, installDir='bin', varDict = None,
                          extraIncPaths=None, extraLibs=None, extraLibPaths=None, extraCflags=None):
      """ Adds a config script to the given package installation.
          varDict - Dictionary of extra variables to define.
      """
      if not self.env['BUILDERS'].has_key("PackageConfigScript"):
         cfg_builder = Builder(action = Action(self.createConfigAction,
                                        lambda t,s,e: "Create config script for %s package: %s"%(self.name, t[0])) )
         self.env.Append(BUILDERS = {"PackageConfigScript" : cfg_builder})
      
      value_dict = {}
      value_dict["prefix"] = self.prefix
      value_dict["extraIncPaths"] = extraIncPaths
      value_dict["extraLibs"] = extraLibs
      value_dict["extraLibPath"] = extraLibPaths
      value_dict["extraCflags"] = extraCflags
                 
      value_dict["varDict"] = varDict
      self.env.PackageConfigScript(target = pj(installDir, name), source = Value(value_dict))
      
      # May need to delay doing this until a later build stage so that all libs, headers, etc are 
      # setup and ready to go in this package.
      

   def addExtraDist(self, files, exclude=[]):
      """
      Adds in the given files to the distribution of this package. If a
      directory is encountered in the file list, it is recursively added. Files
      whose names are in the exclude list are not added to the list.
      """
      for file in files:
         # Make sure to skip files in the exclude list
         if not file in exclude:
            # If the file is a directory, recurse on it
            if os.path.isdir(str(file)):
               self.addExtraDist(os.listdir(str(file)), exclude)
            # If the file is not a directory, add in the extra dist list
            else:
               self.extra_dist.append(file)


   def build(self):
      """
      Sets up the build and install for this package. This will build all
      assemblies contained therein that have not already been built and set 
      up the standard filebundle install.
      """
      for assembly in self.assemblies:
         if not assembly.isBuilt():
            assembly.build()

      # Setup standard file bundle install and add alias to it
      self.fileBundle.buildInstall(self.env, self.prefix)
      Environment().Alias('install', self.prefix)            


def MakeSourceDist(package, baseEnv = None):
   """
   Sets up the distribution build of a source tar.gz for the given package.
   This will put all the required source and extra distribution files into a
   compressed tarball. If an environment is specified, it is copied and the
   copy is used.
   """
   # Clone the base environment if we have one
   if baseEnv:
      env = baseEnv.Copy()
   else:
      env = Environment()


   # Create the distribution filename
   dist_filename = '%s-%d.%d.%d.tar.gz' % (package.getName(),
                                           package.getVersionMajor(),
                                           package.getVersionMinor(),
                                           package.getVersionPatch())

   # Add the tar.gz builder to the environment
   _CreateSourceTarGzBuilder(env)

   # Get a list of the sources that will be included in the distribution
   dist_files = []
   for a in package.getAssemblies():
      dist_files.extend(map(lambda n: n.getFileNode(), a.getHeaders()))
      dist_files.extend(a.getSources())
   dist_files.extend(package.getExtraDist())

   # Setup the build of the distribution
   env.SourceTarGz(dist_filename, dist_files)

   # Mark implicit dependencies on all the files that will be distributed
   env.Depends(dist_filename, dist_files)

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------

def _CreateSourceTarGzBuilder(env):
   import tempfile

   def makeSourceTarGz(target = None, source = None, env = None):
      import os, shutil, tempfile

      # Create the temporary directory
      dist_name = str(target[0])[:-len('.tar.gz')]
      temp_dir = tempfile.mktemp()
      target_dir = path.join(temp_dir, dist_name)

      os.makedirs(target_dir)

      # Copy the sources to the target directory
      for s in source:
         src_file = str(s)
         dest_dir = path.join(target_dir, path.dirname(src_file))
         dest_file = path.basename(src_file)

         # Make sure the target directory exists
         if not os.path.isdir(dest_dir):
            os.makedirs(dest_dir)

         # Copy the file over
         shutil.copy2(src_file, path.join(dest_dir, dest_file))

      # Make the tar.gz
      targz = Action('tar cf - -C '+temp_dir+' $SOURCES | gzip -f > $TARGET')
      targz(target, [File(dist_name)], env)

      # Remove the temporary directory
      shutil.rmtree(temp_dir)

      return None

   # Create the builder and add it to the environment
   source_targz_builder = Builder(action = makeSourceTarGz,
                                  suffix = '.tar.gz')
   env['BUILDERS']['SourceTarGz'] = source_targz_builder
   
   
   
   
   
# ------------------ CONFIG SCRIPT ------------------- #
config_script_contents = '''#!/bin/env python
#
import getopt
import sys

vars = {}

# -- BEGIN CUT --
# config script generated for PACKAGE
vars["Libs"] = "-L/usr/lib -lmylib"
vars["Cflags"] = "-I/include/here -Dmy_VAR"
vars["Version"] = "4.5.0"
vars["Name"] = "My Module"
vars["Description"] = "This is my module over here"
vars["test_var"] = "Test value"
vars["Requires"] = "OtherPackage"
# -- END CUT -- #

def usage():
   print """Usage:
   --libs            output all linker flags
   --cflags          output all compiler flags
   --cflags-only-I   output only the -I flags
   --modversion      get the version of the module
   --modname         get the name of the module
   --moddesc         get the description of the module
   --variable=VAR    get the value of a variable

   --help            display this help message
"""

def getVar(varName):
   if vars.has_key(varName):
      return vars[varName]
   else:
      return ""

def main():
   try:
      opts, args = getopt.getopt(sys.argv[1:], "",
                                 ["help", "libs", "cflags", "cflags-only-I",
                                  "modversion", "modname", "moddesc",
                                  "variable="])
   except getopt.GetoptError:
      usage()
      sys.exit(2)
      
   if not len(opts):
      usage()
      sys.exit()

   ret_val = ""
   
   predefined_opts = { "libs" : "Libs",
                       "cflags" : "Cflags",
                       "modversion" : "Version",
                       "modname" : "Name",
                       "moddesc" : "Description" }
   for o,a in opts:
      if o == "--help":
         usage()
         sys.exit()
      if predefined_opts.has_key(o[2:]):      # Handle standard options
         print getVar(predefined_opts[o[2:]]),
      elif o == "--cflags-only-I":
         cflags = getVar("Cflags")
         cflags_i = [x for x in cflags.split() if x.startswith("-I")]
         print " ".join(cflags_i),
      elif o == "--variable":
         print getVar(a),
         
if __name__=='__main__':
    main()
'''
