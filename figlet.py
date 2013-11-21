# coding=utf-8
import os
import sublime
import sublime_plugin
import sys


here = os.path.dirname(os.path.abspath(__file__))

try:
    import pyfiglet
except ImportError:
    sys.path.append(here)
    import pyfiglet


def figlet_text(text):
    settings = sublime.load_settings("Preferences.sublime-settings")
    font = settings.get('figlet_font', 'standard')

    width = get_width()

    result = pyfiglet.Figlet(font=font, width=width).renderText(text=text)

    # Strip trailing whitespace, because why not?
    if settings.get('figlet_no_trailing_spaces', True):
        result = '\n'.join((line.rstrip() for line in result.split('\n')))

    return result


def get_width():
    # Return width to wrap at (or large number if wrapping not enabled)
    width = 1000000

    view_settings = sublime.active_window().active_view().settings()
    if view_settings.get('word_wrap'):
        output_width = view_settings.get('wrap_width')
        if output_width not in (None, 0):
            width = output_width

    return width


class FigletSelectFontCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.fonts = pyfiglet.FigletFont.getFonts()
        self.window.show_quick_panel(self.fonts, self.on_done)

    def on_done(self, index):
        settings = sublime.load_settings("Preferences.sublime-settings")
        if index != -1:
            # -1 means they closed without picking anything.
            settings.set("figlet_font", self.fonts[index])
            sublime.save_settings("Preferences.sublime-settings")


class FigletTextCommand(sublime_plugin.WindowCommand):
    changed_region = None
    prefix = ''
    init_text = ''

    def run(self):
        self.changed_region = None
        view = self.window.active_view()
        sel = view.sel()
        init_text = '\n'.join(view.substr(region) for region in sel)
        self.init_text = init_text
        r = sel[0]
        cursor = min(r.a, r.b)
        line = view.line(cursor)
        prefix_region = sublime.Region(min(line.a, line.b), cursor)
        prefix = view.substr(prefix_region)
        self.prefix = prefix
        if prefix:
            sel.add(prefix_region)
        if init_text:
            self.on_change(init_text)
        self.window.show_input_panel("Text to Figletize:", init_text,
                                     None, self.on_change, self.on_cancel)

    def figletize(self, text):
        return figlet_text(text)

    def on_change(self, text):
        big_text = self.figletize(text).strip()
        if self.prefix:
            big_text = self.prefix + big_text.replace('\n', '\n' + self.prefix)

        view = self.window.active_view()
        edit = view.begin_edit()

        if self.changed_region is not None:
            view.erase(edit, self.changed_region)
            cursor = self.changed_region.a
        else:
            r = view.sel()[0]
            cursor = min(r.a, r.b)
            for r in reversed(view.sel()):
                view.erase(edit, r)

        view.insert(edit, cursor, big_text)

        # Select
        region = sublime.Region(cursor, cursor + len(big_text))
        self.changed_region = region
        sel = view.sel()
        sel.clear()
        sel.add(region)

        view.end_edit(edit)

    def on_cancel(self):
        if self.changed_region is not None:
            view = self.window.active_view()
            edit = view.begin_edit()
            view.erase(edit, self.changed_region)
            point = self.changed_region.a
            plen = len(self.prefix)
            cursor = point + plen
            sel = view.sel()
            sel.clear()
            if self.prefix or self.init_text:
                view.insert(edit, point, self.prefix + self.init_text)
                if self.init_text:
                    region = sublime.Region(
                        cursor, cursor + len(self.init_text))
                    sel.add(region)
            sel.add(sublime.Region(cursor, cursor))
            view.end_edit(edit)
        self.changed_region = None
        self.init_text = ''
        self.prefix = ''


class FigletTripleQuoteCommand(FigletTextCommand):
    def figletize(self, text):
        return "'''\n%s\n'''" % figlet_text(text).strip()


class FigletCommentCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        if len(view.sel()) == 1 and view.sel()[0].size() > 0:
            s = view.sel()[0]
            text = view.substr(s)

            edit = view.begin_edit()
            view.erase(edit, s)
            self.on_done(text, edit)
        else:
            self.window.show_input_panel("Text to Figletize:", "",
                                         self.on_done, None, None)
        pass

    def on_done(self, text, edit=None):
        if text == "":
            return

        text = figlet_text(text)

        # Put into view, with correct tabbing + one more, and commentize
        view = self.window.active_view()

        if edit is None:
            edit = view.begin_edit()

        self.window.run_command('single_selection')

        cursor = view.sel()[0].a
        current_line = view.line(cursor)
        prefix = view.substr(sublime.Region(current_line.a, cursor))

        text = text[:len(text) - 1]
        text = text.replace("\n", "\n" + prefix)

        view.insert(edit, cursor, text)

        view.sel().add(sublime.Region(cursor, cursor + len(text)))

        # self.window.run_command('split_selection_into_lines')
        self.window.run_command('toggle_comment', {'block': True})

        view.end_edit(edit)
