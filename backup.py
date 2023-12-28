#!/usr/bin/env python

import json
import os
import shutil
import sys
import tempfile
import zipfile
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, List, Set, Tuple, Union

__version__ = "1.3.2"
__all__ = ['BackupManager']

DEFAULT_DENYLIST = {'__pycache__', '.vscode', '.zip', }
NAMEDTEMPORARYFILE_NAME = None

class bcolors:
    HEADER =    '\033[95m'
    OKBLUE =    '\033[94m'
    OKCYAN =    '\033[96m'
    OKGREEN =   '\033[92m'
    WARNING =   '\033[93m'
    FAIL =      '\033[91m'
    ENDC =      '\033[0m'
    BOLD =      '\033[1m'
    UNDERLINE = '\033[4m'


class BackupManager:
    def __init__(self, target:Union[Path, str], save:Union[Path, str], *, 
                                arcname:str=None, 
                                auto_clean:bool=True,
                                required_config:bool=True,
                                dateless:bool=False,
                                preview:bool=False) -> None: 
        """Turn folder or file into zipfile

        Args:
            target (Union[Path, str]): target folder or file
            save (Union[Path, str]): location for save zipfile
            arcname (str, optional): name of the zipfile. If None, then it's name is same as target. Defaults to None.
            auto_clean (bool, optional): auto delete backup files which is no longer needed. Defaults to True.
            required_config (bool, optional): load data from config file. Defaults to True.
            dateless (bool, optional): name zip file without date value. Defaults to False
            preview (bool, optional): display without building zip file. Defaults to False.
        """
        
        self.__target = Path(target).resolve()
        """target folder or file"""
        
        self.__save = Path(save).resolve()
        """location for save zip file"""
        self.__save.mkdir(parents=True, exist_ok=True)
        
        self.__arcname:str
        """name of the zip file"""
        
        self.__required_config = required_config
        """load config while True"""
        
        if arcname is None:
            arcname = self.__target.stem if self.__target.is_file() else self.__target.name
        else:
            arcname = arcname[:-4] if arcname.endswith(".zip") else arcname
        
        self.__dateless = dateless
        if dateless:
            self.__today = None
            self.__arcname = f'{arcname}.zip'
        else:
            self.__today = datetime.now()
            self.__arcname = f'{self.__today.strftime("%Y-%m-%d")}-{arcname}.zip'
            
        
        self.__denylist:Set[str]
        """blacklist of keywords for paths, priority is lower than self.__allowlist"""
        
        self.__allowlist:Set[str] = set()
        """whitelist of keywords for paths, priority is higher than self.__denylist"""
        
        (self.__save/'cache').mkdir(parents=True, exist_ok=True)
        self._cache = self.__save/f'cache/{arcname}.json'
        
        # flags
        self.auto_clean = auto_clean
        """if true, then it will delete every not-montly-latest backup, except this month"""
        
        self.__preview = preview
        """if true, display without building zip file"""
        
        self.__depth_counter = 0
        
        if required_config and self._cache.exists():
            self.__denylist = set()
            info = json.load(self._cache.open('r'))
            self.include(info['allowlist'])
            self.exclude(info['denylist'])
            
            for name in info:
                if name in ['allowlist', 'denylist']:
                    continue
                self.__dict__[name] = info[name]
        else:
            self.__denylist = DEFAULT_DENYLIST.copy()

    def __repr__(self) -> str:
        return f'BackupManager(path="{self.__target}", arcname="{self.__arcname}")'
    
    def __str__(self) -> str:
        return f"{self.__save}/{self.__arcname}"
    
    @property
    def arcname(self):
        """name of the zipfile"""
        
        return self.__arcname[:-4]
    
    @property
    def target(self):
        """target folder or file"""
        
        return str(self.__target)

    @property
    def save(self):
        """save backup location"""
        return str(self.__save)
    
    @property
    def info(self):
        """config dict"""
        
        res = {
            'allowlist' : sorted(self.__allowlist),
            'denylist'  : sorted(self.__denylist) 
        }
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if key in ['allowlist', 'denylist']:
                continue
            res[key] = value
        
        return res
    
    
    def exclude(self, pattern:Union[List[str], Set[str], str]):
        """append the pattern to denylist"""
        if isinstance(pattern, (list, set)):
            self.__denylist.update(pattern)
        else:
            self.__denylist.add(pattern)
        return self
    
    def include(self, pattern:Union[List[str], Set[str], str]):
        """append the pattern to allowlist"""
        if isinstance(pattern, (list, set)):
            self.__allowlist.update(pattern)
        else:
            self.__allowlist.add(pattern)
        return self
        
    def isValid(self, path:Path):
        """check the path is valid due to allowlist and denylist"""
        path = str(path) + '/' if path.is_dir() else str(path)
        res = any(pattern in path for pattern in self.__allowlist)
        return res if res else not any(pattern in path for pattern in self.__denylist)
    
    def __color_path(self, path:str):
        """coloring the path"""
        colors = [bcolors.OKBLUE, bcolors.OKCYAN, bcolors.OKGREEN]
        res = []
        
        is_dir = path[-1] == '/'
        path = path.split('/')
        if is_dir:
            path = path[:-1]
            
        for i in range(len(path)-1):
            res.append(colors[i % len(colors)] + path[i])
        if is_dir:
            i = len(path) - 1
            res.append(colors[i % len(colors)] + path[-1] + '/')
        else:
            res.append(bcolors.WARNING + path[-1])
            
        depth = len(res)
        if depth > self.__depth_counter:
            self.__depth_counter = depth
        
        return '/'.join(res) + bcolors.ENDC
    
    def __namelist(self, path:Path, parent:Path=None)->Generator[Tuple[str, str], Any, None]:
        """list all files and folders from target directory"""
        if not self.isValid(path):
            return
        
        if parent is None:
            parent = Path(path.name)
        else:
            parent = parent/path.name
        
        if path.is_file():
            yield str(path), str(parent)
            return
        
        paths = [p for p in path.iterdir()]
        files = sorted([f for f in paths if f.is_file()], key=lambda x:x.name)
        folders = sorted([d for d in paths if d.is_dir()], key=lambda x:x.name)

        yield str(path)+'/', str(parent)+'/'
        for file in files:
            yield from self.__namelist(file, parent)
        del files
        
        for folder in folders:
            yield from self.__namelist(folder, parent)
    
    @property
    def namelist(self):
        """list all files and folders from target directory"""
        return [path[0] for path in self.__namelist(self.__target)]
    
    @property
    def arcnamelist(self):
        """list all files and folders from save zipfile"""
        return [path[1] for path in self.__namelist(self.__target)]
    
    def __find_files(self) -> List[Tuple[Path, datetime]]:
        """find all backups contains same name with arcname"""
        target = self.__arcname[11:-4]
        for file in self.__save.iterdir():
            if file.is_dir() or file.suffix != '.zip':
                continue
            _date = file.name[:10].split('-')
            if len(_date) != 3:
                continue
            date = datetime(year=int(_date[0]), month=int(_date[1]), day=int(_date[2]))

            # 强一致性
            name = file.name[11:-4]
            if name == target:
                yield file, date
    
    def __auto_clean(self):
        """delete every not-montly-latest backup, except this month"""
        
        if self.__dateless:
            return
        
        print('\ntriggered auto_clean process', file=sys.stderr)
        files:List[Tuple[Path, datetime]] = []
        
        # get all backup files
        for path, date in self.__find_files():
            if date.year < self.__today.year or date.month < self.__today.month:
                files.append((path, date))
        
        if len(files) < 2:
            print('done', file=sys.stderr)
            return
        
        files.sort(key=lambda x : x[1], reverse=True)
        res = files[0][1] # latest date
        
        for path, date in files[1:]:
            if date.month == res.month and date.year == res.year:
                path.unlink()
                print(bcolors.FAIL + 'delete' + bcolors.WARNING, path.name, bcolors.ENDC, file=sys.stderr)
            res = date
        print('done', file=sys.stderr, flush=True)
    
    def __save_config(self):
        with self._cache.open('w') as f:
            json.dump(self.info, f, indent=4)
    
    def compress(self, compression:int=zipfile.ZIP_DEFLATED, compresslevel:int=9):
        global NAMEDTEMPORARYFILE_NAME
        
        print(f'\nconstructing {self.__save}/{self.__arcname}\n', file=sys.stderr)

        if self.__required_config:
            if not self._cache.exists():
                self.__save_config()
                print(f'{self._cache} not found\nconfig file constructed\nskip compression')
                return
            self.__save_config()

        total_file_size = 0
        total_compress_size = 0

        temp = tempfile.NamedTemporaryFile(prefix=self.target.split('/')[-1]+'_', dir=str(self.__save), mode='wb', delete=False)
        NAMEDTEMPORARYFILE_NAME = temp.name
        
        if self.__preview:
            for filename, arcname in self.__namelist(self.__target):
                file_size = os.path.getsize(filename) if os.path.isfile(filename) else None
                print(self.__color_path(arcname), f'({file_size})' if file_size else '', flush=True, file=sys.stderr)
            return
            
        with zipfile.ZipFile(temp, mode='w',
                                compression=compression, 
                                compresslevel=compresslevel) as archive:

            for filename, arcname in self.__namelist(self.__target):
                file_size = os.path.getsize(filename)
                total_file_size += file_size
                
                if os.path.isfile(filename):
                    print(self.__color_path(arcname), f'({file_size} -> ', end='', flush=True, file=sys.stderr)
                else:
                    print(self.__color_path(arcname), file=sys.stderr)
                
                archive.write(filename=filename, arcname=arcname)

                if os.path.isfile(filename):
                    file_info = archive.getinfo(arcname)
                    if file_size > 0:
                        compress_size = file_info.compress_size
                        total_compress_size += compress_size
                        print('%d deflate %.2f%%)'%(compress_size, (file_size-compress_size)/file_size*100), file=sys.stderr)
                    else:
                        print('0 deflate 0%)', file=sys.stderr)
        
        temp.close()
        
        shutil.move(NAMEDTEMPORARYFILE_NAME, f'{self.__save}/{self.__arcname}')
        NAMEDTEMPORARYFILE_NAME = None
        
        if total_file_size > 0:
            print('total deflate', '%.2f%%'%((total_file_size - total_compress_size)/total_file_size*100), file=sys.stderr)
            print('max depth', self.__depth_counter, file=sys.stderr)
        
        if self.auto_clean:
            self.__auto_clean()

        return self

def main():
    parser = ArgumentParser(description="""Tool for building zip files. 
                            It required a json file for construction. 
                            If there's no json file, then it will build one, then skip the current zip file construction.""")
    parser.add_argument('save', help='save location for zipfiles')
    parser.add_argument('-f',           action='append', nargs=1, metavar='PATH',           help='fast zip, required a directory')
    parser.add_argument('-n',           action='append', nargs=2, metavar=('PATH', 'NAME'), help='named zip, required a directory and a name of zip file')
    parser.add_argument('--force',      action='store_true', help='global optional, build zipfiles without config')
    parser.add_argument('--dateless',   action='store_true', help='global optional, naming zipfiles without date')
    parser.add_argument('--preview',    action='store_true', help='global optional, display without building zip file')
    args = parser.parse_args()
    
    save = args.save
    if os.path.isabs(save):
        save = Path(save)
    else:
        root = Path(__file__).resolve().parent
        save = (root/save).resolve()
    save.mkdir(parents=True, exist_ok=True)
    
    force = args.force
    dateless = args.dateless
    
    if not args.f is None:
        for path in args.f:
            path = Path(path[0]).resolve()
            BackupManager(path, save, 
                          auto_clean=not force, 
                          required_config=not force, 
                          dateless=dateless,
                          preview=args.preview).compress()
        
    if not args.n is None:
        for path, name in args.n:
            path = Path(path).resolve()
            BackupManager(path, save, arcname=name, 
                          auto_clean=not force, 
                          required_config=not force, 
                          dateless=dateless,
                          preview=args.preview).compress()


            
if __name__ == "__main__":
    
    try:
        main()
    except KeyboardInterrupt:
        if not NAMEDTEMPORARYFILE_NAME is None:  
            print('\nremoved temp file', NAMEDTEMPORARYFILE_NAME, file=sys.stderr)
            os.unlink(NAMEDTEMPORARYFILE_NAME)
        print(file=sys.stderr)