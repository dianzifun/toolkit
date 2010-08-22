#ifndef PIX_CORE_H_
#define PIX_CORE_H_

#include <string>
#include <vector>
#include <map>
#include <utility>

#include "sqlite3/sqlite3.h"

#include "utils.h"
#include "mylock.h"
#include "pixlibrary.h"
#include "pixalbum.h"
#include "pixtag.h"
#include "pagingtree.h"

class PixCore {

public:
  explicit PixCore(const std::string& fn);
  ~PixCore();

  std::vector<PixAlbum> listAlbums(bool refresh = false);

  void reloadAlbums() {
    this->listAlbums(true);
  }

  bool hasAlbum(const std::string& aname);

  int addAlbum(const std::string& aname);

  int removeAlbum(const std::string& aname);

  int renameAlbum(const std::string& oldName, const std::string& newName);

  int getAlbum(const std::string& aname, PixAlbum& album);

  std::vector<PixLibrary> listLibraries(bool refresh = false);

  void reloadLibraries() {
    this->listLibraries(true);
  }

  bool hasLibrary(const std::string& lname);

  int addLibrary(const std::string& lname);

  int removeLibrary(const std::string& lname);

  int renameLibrary(const std::string& oldName, const std::string& newName);

  int getLibrary(const std::string& lname, PixLibrary& library);

  std::vector<PixTag> listTags(bool refresh = false);

  void reloadTags() {
    this->listTags(true);
  }

  bool hasTag(const std::string& tname);

  int addTag(const std::string& tname);

  int removeTag(const std::string& tname);

  int renameTag(const std::string& oldName, const std::string& newName);

  int getTag(const std::string& tname, PixTag& tag);

  bool hasSetting(const std::string& key);

  int getSetting(const std::string& key, std::string& value);

  int setSetting(const std::string& key, const std::string& value);

  std::vector<std::pair<std::string, std::string> > listSettings(bool refresh = false);

  void reloadSettings() {
    this->listSettings(true);
  }

private:

  DISALLOW_ASSIGNMENT(PixCore)

  std::string fname;
  std::vector<PixAlbum> cachedAlbums;
  MyLock cachedAlbumsLock;
  std::vector<PixLibrary> cachedLibraries;
  MyLock cachedLibrariesLock;
  std::vector<PixTag> cachedTags;
  MyLock cachedTagsLock;
  std::map<std::string, std::string> cachedSettings;
  MyLock cachedSettingsLock;
  sqlite3* conn;
  MyLock connLock;
};

#endif  // PIX_CORE_H_
