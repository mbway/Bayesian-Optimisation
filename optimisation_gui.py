#!/usr/bin/env python3
'''
GUI utilities to be used with the optimisation module.
'''
from __future__ import print_function


import sys
if sys.version_info[0] == 3: # python 3
    import PyQt5.QtCore as qtc
    import PyQt5.QtGui as qtg
    import PyQt5.QtWidgets as qt
elif sys.version_info[0] == 2: # python 2
    # Qt5 is not available in python 2
    import PyQt4.QtCore as qtc
    import PyQt4.QtGui as qt
    import PyQt4.QtGui as qtg
else:
    print('unsupported python version')


import sys
import signal
import threading

import optimisation as op


class BetterQThread(qtc.QThread):
    '''
    construct a QThread using a similar API to the threading module
    '''
    def __init__(self, target, args=None):
        super(BetterQThread, self).__init__()
        self.args = [] if args is None else args
        self.target = target
    def run(self):
        self.target(*self.args)

class ScrollTextEdit(qt.QTextEdit):
    '''
    a QTextEdit with helper functions to provide nice scrolling, ie only keep
    scrolling to the bottom as new text is added if the end of the text box was
    visible before the text was added
    '''
    def end_is_visible(self):
        bar = self.verticalScrollBar()
        return bar.maximum() - bar.value() < bar.singleStep()
    def scroll_to_end(self):
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

def format_matching(doc, search, fmt, whole_line=True):
    '''
    apply the given format to lines matching the search query

    doc: QTextDocument to search through
    search: string or QRegExp to search for in the document
    fmt: QTextCharFormat to apply to the matching ranges
    whole_line: whether to apply the formatting to the whole line or just
                the matching text
    '''
    hl = qtg.QTextCursor(doc)
    while not hl.isNull() and not hl.atEnd():
        hl = doc.find(search, hl)
        if not hl.isNull():
            # the text between the anchor and the position will be selected
            if whole_line:
                hl.movePosition(qtg.QTextCursor.StartOfLine)
                hl.movePosition(qtg.QTextCursor.EndOfLine, qtg.QTextCursor.KeepAnchor)
            # merge the char format with the current format
            hl.mergeCharFormat(fmt)

def start_GUI(e_or_o):
    '''
    start a GUI for the given evaluator or optimiser and wait for it to close
    '''
    app = qt.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    gui = None
    if isinstance(e_or_o, op.Evaluator):
        gui = EvaluatorGUI(e_or_o)
    elif isinstance(e_or_o, op.Optimiser):
        gui = OptimiserGUI(e_or_o)
    else:
        raise TypeError

    def handle_ctrl_c(*args):
        gui.close()
        app.quit()
    signal.signal(signal.SIGINT, handle_ctrl_c)

    sys.exit(app.exec_())

class LoggableGUI(qt.QWidget):
    def __init__(self):
        super(LoggableGUI, self).__init__()

        self.label_font = qtg.QFont(qtg.QFont().defaultFamily(), 10)

        grid = qt.QGridLayout()
        grid.setSpacing(5)

        self.last_log_length = 0 # length of log string as of last update
        self.log = ScrollTextEdit()
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(qt.QTextEdit.NoWrap)
        self.log.setFont(qtg.QFontDatabase.systemFont(qtg.QFontDatabase.FixedFont))
        grid.addWidget(self.log, 0, 0)

        self.watcher = qtc.QTimer()
        self.watcher.setInterval(500) # ms
        self.watcher.timeout.connect(self.update_UI)
        self.watcher.start() # set the timer going

        # fit the sidebar layout inside a widget to control the width
        sidebarw = qt.QWidget()
        sidebarw.setFixedWidth(200)
        grid.addWidget(sidebarw, 0, 1)

        self.sidebar = qt.QVBoxLayout()
        sidebarw.setLayout(self.sidebar)

        self.setLayout(grid)
        self.resize(1024, 768)
        self._center()

        self.raw = qt.QTextEdit(self)
        self.raw.setWindowFlags(self.raw.windowFlags() | qtc.Qt.Window)
        self.raw.setReadOnly(True)
        self.raw.resize(1600, 900)
        self.raw.move(100, 100)

    def format_text(self):
        '''
        change the formatting on the text to highlight important words
        '''
        doc = self.log.document()
        color = qtg.QTextCursor(doc).charFormat()
        color.setForeground(qtc.Qt.red)

        problems = qtc.QRegExp(r'(problem|error|exception|traceback)')
        problems.setCaseSensitivity(qtc.Qt.CaseInsensitive)

        format_matching(doc, problems, color, whole_line=True)

    def update_log(self, text):
        '''
        make the log edit area reflect the current text.
        Note: it is assumed that the log can only be appended to and not
              otherwise modified
        '''
        new_len = len(text)
        was_at_end = self.log.end_is_visible()
        if new_len > self.last_log_length:
            new_text = text[self.last_log_length:]

            # just using self.log.append() will add an implicit newline
            cur = qtg.QTextCursor(self.log.document())
            cur.movePosition(qtg.QTextCursor.End)
            cur.insertText(new_text)

            self.last_log_length = new_len

        if was_at_end:
            self.log.scroll_to_end()

        self.format_text()

    def _show_raw(self, dict_, exclude):
        s = ''
        for k, v in sorted(dict_.items(), key=lambda x: x[0]):
            if k in exclude:
                s += '{}: skipped\n\n\n'.format(k)
            else:
                if isinstance(v, threading.Event):
                    v = '{}: set={}'.format(type(v), v.is_set())
                if isinstance(v, list):
                    list_str = '[\n' + ',\n'.join([str(x) for x in v]) + '\n]'
                    v = 'len = {}\n{}'.format(len(v), list_str)
                s += '{}:\n{}\n\n'.format(k, v)
        self.raw.setText(s)
        self.raw.show()

    def _center(self):
        frame = self.frameGeometry()
        frame.moveCenter(qt.QDesktopWidget().availableGeometry().center())
        self.move(frame.topLeft())
    def _add_named_field(self, name, default_value, font=None):
        ''' add a label and a line edit to the sidebar '''
        font = self.label_font if font is None else font
        label = qt.QLabel(name)
        label.setFont(font)
        self.sidebar.addWidget(label)
        edit = qt.QLineEdit(default_value)
        self.sidebar.addWidget(edit)
        return edit
    def _add_button(self, name, onclick):
        ''' add a button to the sidebar '''
        button = qt.QPushButton(name)
        button.clicked.connect(onclick)
        self.sidebar.addWidget(button)
        return button


class EvaluatorGUI(LoggableGUI):
    def __init__(self, evaluator, name=None):
        super(EvaluatorGUI, self).__init__()
        assert isinstance(evaluator, op.Evaluator)

        self.evaluator = evaluator
        self.evaluator_thread = BetterQThread(target=self._run_evaluator)
        self.evaluator_thread.setTerminationEnabled(True)

        if name is None:
            self.setWindowTitle('Evaluator GUI')
        else:
            self.setWindowTitle('Evaluator GUI: {}'.format(name))
        self.name = name


        self.host = self._add_named_field('host:', op.DEFAULT_HOST)
        self.port = self._add_named_field('port:', str(op.DEFAULT_PORT))

        self._add_button('Start Client', self.start)
        self._add_button('Stop Client', self.stop)
        self._add_button('Force Stop', self.force_stop)

        self.info = qt.QLabel('')

        self.sidebar.addSpacing(20)

        self._add_button('Show Raw', self.show_raw)

        self.sidebar.addStretch() # fill remaining space

        self.update_UI()
        self.log.scroll_to_end()

        self.show()

    def _run_evaluator(self):
        host = self.host.text()
        port = int(self.port.text())
        self.evaluator.run_client(host, port)

    def set_info(self, text):
        self.info.setText(text)
        print('{} info: {}'.format(self.name, text), flush=True)

    def update_UI(self):
        self.update_log(self.evaluator.log_record)

    def start(self):
        if self.evaluator_thread.isRunning():
            self.set_info('evaluator already running')
        else:
            self.evaluator_thread.start()
    def stop(self):
        self.evaluator.stop()
    def force_stop(self):
        self.evaluator.stop()
        self.evaluator_thread.terminate()

    def show_raw(self):
        self._show_raw(self.evaluator.__dict__, exclude=['log_record'])

    def closeEvent(self, event):
        if self.evaluator_thread.isRunning():
            self.set_info('shutting down')
            self.evaluator.stop()
            self.evaluator_thread.wait(time=5000) # ms
        self.raw.close()
        event.accept()


class OptimiserGUI(LoggableGUI):
    def __init__(self, optimiser, name=None):
        super(OptimiserGUI, self).__init__()
        assert isinstance(optimiser, op.Optimiser)

        self.optimiser = optimiser
        self.optimiser_thread = BetterQThread(target=self._run_optimiser)
        self.optimiser_thread.setTerminationEnabled(True)

        if name is None:
            self.setWindowTitle('Optimiser GUI')
        else:
            self.setWindowTitle('Optimiser GUI: {}'.format(name))
        self.name = name

        self.host = self._add_named_field('host:', op.DEFAULT_HOST)
        self.port = self._add_named_field('port:', str(op.DEFAULT_PORT))
        self._add_button('Start Server', self.start)
        self._add_button('Stop Server', self.stop)
        self._add_button('Force Stop', self.force_stop)

        self.sidebar.addSpacing(20)

        self.checkpoint_filename = self._add_named_field(
            'filename:', optimiser.checkpoint_filename)

        self._add_button('Save Checkpoint', self.save_checkpoint)
        self._add_button('Load Checkpoint', self.load_checkpoint)

        self.info = qt.QLabel('')

        self.sidebar.addSpacing(20)

        self._add_button('Show Raw', self.show_raw)

        self.sidebar.addStretch() # fill remaining space

        self.update_UI()
        self.log.scroll_to_end()

        self.show()

    def _run_optimiser(self):
        host = self.host.text()
        port = int(self.port.text())
        self.optimiser.run_server(host, port)

    def set_info(self, text):
        self.info.setText(text)
        print('{} info: {}'.format(self.name, text), flush=True)

    def update_UI(self):
        self.update_log(self.optimiser.log_record)

    def start(self):
        if self.optimiser_thread.isRunning():
            self.set_info('optimiser already running')
        else:
            self.optimiser_thread.start()
    def stop(self):
        self.optimiser.stop()
    def force_stop(self):
        self.optimiser.stop()
        self.optimiser_thread.terminate()

    def show_raw(self):
        self._show_raw(self.optimiser.__dict__, exclude=['log_record'])

    def save_checkpoint(self):
        filename = self.checkpoint_filename.text()
        self.optimiser.save_when_ready(filename)
    def load_checkpoint(self):
        filename = self.checkpoint_filename.text()
        self.optimiser.stop()
        self.optimiser.load_checkpoint(filename)

    def closeEvent(self, event):
        if self.optimiser_thread.isRunning():
            self.set_info('shutting down')
            self.optimiser.stop()
            self.optimiser_thread.wait(5000) # ms
        self.raw.close()
        event.accept()





class DebugGUIs(qtc.QObject):
    '''
    a debug/helper class for quickly spawning GUIs for the given optimisers and
    evaluators which run in a separate thread.
    Example usage:
    >>> guis = op_gui.DebugGUIs([optimiser1, optimiser2], evaluator)
    >>> # do some stuff
    >>> guis.stop()

    '''

    # signal must be defined at the class for subclass of QObject, but still
    # access through self.add_signal
    add_signal = qtc.pyqtSignal(object, name='add_signal')

    def __init__(self, optimisers, evaluators):
        '''
        optimisers: may be either a list or a single optimiser
        evaluators: may be either a list or a single evaluator
        '''
        super(DebugGUIs, self).__init__()
        self.optimisers = self._ensure_list(optimisers)
        self.evaluators = self._ensure_list(evaluators)
        self.guis = []
        # counters for naming
        self.op_counter = 1
        self.ev_counter = 1
        self.ready = threading.Event()
        self.app_thread = threading.Thread(target=self._start)
        self.app_thread.setDaemon(True)
        self.app_thread.start()
        self.ready.wait()

    def _ensure_list(self, x):
        ''' return x if x is iterable, otherwise return [x] '''
        try:
            iter(x)
            return x
        except TypeError:
            return [x]

    def _start(self):
        self.app = qt.QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(True)

        # must be queued to be used from non-Qt threads
        self.add_signal.connect(self._add, qtc.Qt.QueuedConnection)

        for o in self.optimisers:
            assert isinstance(o, op.Optimiser)
            self._add(o)

        for e in self.evaluators:
            assert isinstance(e, op.Evaluator)
            self._add(e)

        self.ready.set()
        self.app.exec_()

    def _add(self, e_or_o):
        '''
        e_or_o: an Evaluator or Optimiser to spawn a GUI for
        '''
        if isinstance(e_or_o, op.Optimiser):
            self.guis.append(OptimiserGUI(e_or_o, str(self.op_counter)))
            print('spawning optimiser GUI {}'.format(self.op_counter))
            self.op_counter += 1
        elif isinstance(e_or_o, op.Evaluator):
            self.guis.append(EvaluatorGUI(e_or_o, str(self.ev_counter)))
            print('spawning evaluator GUI {}'.format(self.ev_counter))
            self.ev_counter += 1
        else:
            raise TypeError

    def add(self, e_or_o):
        # NOTE: this doesn't actually work. The window opens but does not update
        print('signalling to add')
        self.add_signal.emit(e_or_o)
        # forces Qt to process the event
        qtc.QEventLoop().processEvents()

    def stop(self):
        for g in self.guis:
            g.close()
        self.t.exit()
        self.app.quit()
        self.app_thread.join()
    def wait(self):
        print('waiting for GUIs to manually close', flush=True)
        self.app_thread.join()



def main():
    '''
    example of the module usage
    '''

    ranges = {'a':[1,2], 'b':[3,4]}
    class TestEvaluator(op.Evaluator):
        def test_config(self, config):
            return config.a # placeholder cost function
    optimiser = op.GridSearchOptimiser(ranges, order=['a','b'])
    evaluator = TestEvaluator()

    app = qt.QApplication(sys.argv)

    op_gui = OptimiserGUI(optimiser)
    ev_gui = EvaluatorGUI(evaluator)

    def handle_ctrl_c(*args):
        op_gui.close()
        ev_gui.close()
        app.quit()
    signal.signal(signal.SIGINT, handle_ctrl_c)

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

