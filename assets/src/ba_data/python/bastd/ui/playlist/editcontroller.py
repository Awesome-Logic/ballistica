# Copyright (c) 2011-2020 Eric Froemling
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# -----------------------------------------------------------------------------
"""Defines a controller for wrangling playlist edit UIs."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

import ba

if TYPE_CHECKING:
    from typing import Any, Type, List, Dict, Optional


class PlaylistEditController:
    """Coordinates various UIs involved in playlist editing."""

    def __init__(self,
                 sessiontype: Type[ba.Session],
                 existing_playlist_name: str = None,
                 transition: str = 'in_right',
                 playlist: List[Dict[str, Any]] = None,
                 playlist_name: str = None):
        from ba.internal import preload_map_preview_media, filter_playlist
        from bastd.ui import playlist as playlistui
        from bastd.ui.playlist import edit as peditui

        bs_config = ba.app.config

        # Since we may be showing our map list momentarily,
        # lets go ahead and preload all map preview textures.
        preload_map_preview_media()
        self._sessiontype = sessiontype

        self._editing_game = False
        self._editing_game_type: Optional[Type[ba.GameActivity]] = None
        self._pvars = playlistui.PlaylistTypeVars(sessiontype)
        self._existing_playlist_name = existing_playlist_name
        self._config_name_full = self._pvars.config_name + ' Playlists'

        # Make sure config exists.
        if self._config_name_full not in bs_config:
            bs_config[self._config_name_full] = {}

        self._selected_index = 0
        if existing_playlist_name:
            self._name = existing_playlist_name

            # Filter out invalid games.
            self._playlist = filter_playlist(
                bs_config[self._pvars.config_name +
                          ' Playlists'][existing_playlist_name],
                sessiontype=sessiontype,
                remove_unowned=False)
            self._edit_ui_selection = None
        else:
            if playlist is not None:
                self._playlist = playlist
            else:
                self._playlist = []
            if playlist_name is not None:
                self._name = playlist_name
            else:

                # Find a good unused name.
                i = 1
                while True:
                    self._name = (
                        self._pvars.default_new_list_name.evaluate() +
                        ((' ' + str(i)) if i > 1 else ''))
                    if self._name not in bs_config[self._pvars.config_name +
                                                   ' Playlists']:
                        break
                    i += 1

            # Also we want it to start with 'add' highlighted since its empty
            # and that's all they can do.
            self._edit_ui_selection = 'add_button'

        ba.app.main_menu_window = (peditui.PlaylistEditWindow(
            editcontroller=self, transition=transition).get_root_widget())

    def get_config_name(self) -> str:
        """(internal)"""
        return self._pvars.config_name

    def get_existing_playlist_name(self) -> Optional[str]:
        """(internal)"""
        return self._existing_playlist_name

    def get_edit_ui_selection(self) -> Optional[str]:
        """(internal)"""
        return self._edit_ui_selection

    def set_edit_ui_selection(self, selection: str) -> None:
        """(internal)"""
        self._edit_ui_selection = selection

    def get_name(self) -> str:
        """(internal)"""
        return self._name

    def set_name(self, name: str) -> None:
        """(internal)"""
        self._name = name

    def get_playlist(self) -> List[Dict[str, Any]]:
        """Return the current state of the edited playlist."""
        return copy.deepcopy(self._playlist)

    def set_playlist(self, playlist: List[Dict[str, Any]]) -> None:
        """Set the playlist contents."""
        self._playlist = copy.deepcopy(playlist)

    def get_session_type(self) -> Type[ba.Session]:
        """Return the ba.Session type for this edit-session."""
        return self._sessiontype

    def get_selected_index(self) -> int:
        """Return the index of the selected playlist."""
        return self._selected_index

    def get_default_list_name(self) -> ba.Lstr:
        """(internal)"""
        return self._pvars.default_list_name

    def set_selected_index(self, index: int) -> None:
        """Sets the selected playlist index."""
        self._selected_index = index

    def add_game_pressed(self) -> None:
        """(internal)"""
        from bastd.ui.playlist import addgame
        ba.containerwidget(edit=ba.app.main_menu_window, transition='out_left')
        ba.app.main_menu_window = (addgame.PlaylistAddGameWindow(
            editcontroller=self).get_root_widget())

    def edit_game_pressed(self) -> None:
        """Should be called by supplemental UIs when a game is to be edited."""
        from ba.internal import getclass
        if not self._playlist:
            return
        self._show_edit_ui(gametype=getclass(
            self._playlist[self._selected_index]['type'],
            subclassof=ba.GameActivity),
                           config=self._playlist[self._selected_index])

    def add_game_cancelled(self) -> None:
        """(internal)"""
        from bastd.ui.playlist import edit as pedit
        ba.containerwidget(edit=ba.app.main_menu_window,
                           transition='out_right')
        ba.app.main_menu_window = (pedit.PlaylistEditWindow(
            editcontroller=self, transition='in_left').get_root_widget())

    def _show_edit_ui(self, gametype: Type[ba.GameActivity],
                      config: Optional[Dict[str, Any]]) -> None:
        self._editing_game = (config is not None)
        self._editing_game_type = gametype
        assert self._sessiontype is not None
        gametype.create_config_ui(self._sessiontype, copy.deepcopy(config),
                                  self._edit_game_done)

    def add_game_type_selected(self, gametype: Type[ba.GameActivity]) -> None:
        """(internal)"""
        self._show_edit_ui(gametype=gametype, config=None)

    def _edit_game_done(self, config: Optional[Dict[str, Any]]) -> None:
        from bastd.ui.playlist import edit as pedit
        from bastd.ui.playlist import addgame
        from ba.internal import get_type_name
        if config is None:
            # If we were editing, go back to our list.
            if self._editing_game:
                ba.playsound(ba.getsound('powerdown01'))
                ba.containerwidget(edit=ba.app.main_menu_window,
                                   transition='out_right')
                ba.app.main_menu_window = (pedit.PlaylistEditWindow(
                    editcontroller=self,
                    transition='in_left').get_root_widget())

            # Otherwise we were adding; go back to the add type choice list.
            else:
                ba.containerwidget(edit=ba.app.main_menu_window,
                                   transition='out_right')
                ba.app.main_menu_window = (addgame.PlaylistAddGameWindow(
                    editcontroller=self,
                    transition='in_left').get_root_widget())
        else:
            # Make sure type is in there.
            assert self._editing_game_type is not None
            config['type'] = get_type_name(self._editing_game_type)

            if self._editing_game:
                self._playlist[self._selected_index] = copy.deepcopy(config)
            else:
                # Add a new entry to the playlist.
                insert_index = min(len(self._playlist),
                                   self._selected_index + 1)
                self._playlist.insert(insert_index, copy.deepcopy(config))
                self._selected_index = insert_index

            ba.playsound(ba.getsound('gunCocking'))
            ba.containerwidget(edit=ba.app.main_menu_window,
                               transition='out_right')
            ba.app.main_menu_window = (pedit.PlaylistEditWindow(
                editcontroller=self, transition='in_left').get_root_widget())
