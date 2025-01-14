from piscat.Preproccessing.normalization import Normalization
from piscat.BackgroundCorrection.DRA import DifferentialRollingAverage

from piscat.GUI.BackgroundCorrection import DRA
from piscat.GUI.Visualization.fun_display_localization import Visulization_localization
from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6.QtCore import *


class FUN_DRA(QtWidgets.QMainWindow, QtCore.QObject):

    update_output = QtCore.Signal(object)
    update_pn_roi = QtCore.Signal(object)
    set_new_text = QtCore.Signal(object)
    set_plain_text = QtCore.Signal(object)

    def __init__(self, video, object_update_progressBar):
        super().__init__()

        self.threadpool = QThreadPool()

        self.original_video = video
        self.original_video_pn = None
        self.object_update_progressBar = object_update_progressBar
        self.DRA_video = None
        self.flag_thread_dra = True
        self.flag_update_original_video = True
        self.flag_update_pn_video = False

    @Slot()
    def thread_DRA_complete(self):
        self.object_update_progressBar.setRange(self.p_max)
        self.object_update_progressBar.setLabel('')
        self.thread_DRA.signals.DRA_complete_signal.emit(False)
        self.flag_thread_dra = False
        print("THREAD DRA COMPLETE!")

    @Slot()
    def result_tread_DRA(self, result):
        self.DRA_video = result
        self.flag_update_dra = False
        print("DRA video update!")

    @Slot()
    def update_original_video(self, video):
        if self.flag_update_pn_video:
            self.original_video_pn = video[0]
            self.flag_update_pn_video = False
            self.flag_update_original_video = False

        else:
            self.original_video = video[0]
            self.flag_update_original_video = False

    @Slot()
    def startProgressBar(self, instance, **kwargs):
        self.thread_DRA = instance(**kwargs)
        self.thread_DRA.signals.updateProgress_DRA.connect(self.object_update_progressBar.setProgress)
        self.thread_DRA.signals.result_final.connect(self.result_tread_DRA)
        self.thread_DRA.signals.finished_DRA.connect(self.thread_DRA_complete)

        self.threadpool.start(self.thread_DRA)

    def dra_wrapper(self):
        title = ''

        if self.original_video is not None and self.original_video.shape[0] - (2 * self.info_DRA.batch_size) <= 0:
            self.msg_box = QtWidgets.QMessageBox()
            self.msg_box.setWindowTitle("Warning!")
            self.msg_box.setText(
                "The batch size bigger than the video length (#frame" + str(self.original_video.shape[0]) + ")!")
            self.msg_box.exec_()

        if self.original_video is not None and self.original_video.shape[0] - (2 * self.info_DRA.batch_size) > 0:

            if self.info_DRA.flag_power_normalization:
                self.set_new_text.emit("Start PN -->")

                self.flag_update_original_video = True
                self.flag_update_pn_video = True
                worker = Normalization(self.original_video, flag_pn=True)
                worker.signals.result.connect(self.update_original_video)
                self.threadpool.start(worker)
                while self.flag_update_original_video:
                    QtCore.QCoreApplication.processEvents()

                self.flag_update_original_video = True
                title = title + 'PN_'
                self.set_plain_text.emit(" Done")

            self.p_max = self.original_video.shape[0] - (2 * self.info_DRA.batch_size) - 1
            self.object_update_progressBar.setProgress(0)
            self.object_update_progressBar.setRange(self.p_max)

            if self.info_DRA.flag_FPN:
                self.set_new_text.emit("Start DRA + " + self.info_DRA.mode_FPN + '-->')
                if self.info_DRA.flag_power_normalization:
                    d_arg = {'video': self.original_video_pn, 'batchSize': self.info_DRA.batch_size, 'flag_GUI': True,
                             'instance': DifferentialRollingAverage, 'FPN_flag': True, 'select_correction_axis': self.info_DRA.axis,
                             'object_update_progressBar': self.object_update_progressBar, 'mode_FPN': self.info_DRA.mode_FPN}
                else:
                    d_arg = {'video': self.original_video, 'batchSize': self.info_DRA.batch_size, 'flag_GUI': True,
                             'instance': DifferentialRollingAverage, 'FPN_flag': True, 'select_correction_axis': self.info_DRA.axis,
                             'object_update_progressBar': self.object_update_progressBar, 'mode_FPN': self.info_DRA.mode_FPN}

                title = title + self.info_DRA.mode_FPN + '_'

            else:
                self.set_new_text.emit("Start DRA -->")
                if self.info_DRA.flag_power_normalization:
                    d_arg = {'video': self.original_video_pn, 'batchSize': self.info_DRA.batch_size, 'flag_GUI': True,
                             'instance': DifferentialRollingAverage, 'FPN_flag': False, 'select_correction_axis': self.info_DRA.axis,
                             'object_update_progressBar': self.object_update_progressBar, 'mode_FPN': self.info_DRA.mode_FPN}
                else:

                    d_arg = {'video': self.original_video, 'batchSize': self.info_DRA.batch_size, 'flag_GUI': True,
                             'instance': DifferentialRollingAverage, 'FPN_flag': False, 'select_correction_axis': self.info_DRA.axis,
                             'object_update_progressBar': self.object_update_progressBar, 'mode_FPN': self.info_DRA.mode_FPN}

            self.flag_thread_dra = True
            self.flag_update_dra = True
            self.startProgressBar(**d_arg)

            while self.flag_thread_dra:
                QtCore.QCoreApplication.processEvents()

            while self.flag_update_dra:
                QtCore.QCoreApplication.processEvents()

            self.set_plain_text.emit(" Done")

            title = title + 'DRA'

            if self.info_DRA.flag_display:
                self.visualization_ = Visulization_localization()
                self.visualization_.new_display(self.DRA_video, self.DRA_video, object=None, title=title)

            self.update_output.emit([self.DRA_video, title, None, self.info_DRA.batch_size])

        else:
            self.msg_box = QtWidgets.QMessageBox()
            self.msg_box.setWindowTitle("Warning!")
            self.msg_box.setText("Please load one video!")
            self.msg_box.exec_()

    def apply_DRA(self):
        self.info_DRA = DRA()
        self.info_DRA.signal_finish.connect(self.run_DRA_wrapper)

    def run_DRA_wrapper(self, flag):
        if flag:
            self.info_DRA.window.close()
            self.dra_wrapper()

    def run_DRA_from_bgtabs(self, mode_FPN, batch_size, flag_power_normalization, roi_x_pn, roi_y_pn, flag_FPN, axis):
        title = ''

        if self.original_video is not None and self.original_video.shape[0] - (2 * batch_size) <= 0:
            self.msg_box = QtWidgets.QMessageBox()
            self.msg_box.setWindowTitle("Warning!")
            self.msg_box.setText(
                "The batch size bigger than the video length (#frame" + str(self.original_video.shape[0]) + ")!")
            self.msg_box.exec_()

        if self.original_video is not None and self.original_video.shape[0] - (2 * batch_size) > 0:

            if flag_power_normalization:
                self.set_new_text.emit("Start PN -->")
                self.flag_update_original_video = True
                self.flag_update_pn_video = True

                worker = Normalization(self.original_video, flag_pn=True)
                self.update_pn_roi.connect(worker.update_class_parameter)
                worker.signals.result.connect(self.update_original_video)
                self.update_pn_roi.emit([roi_x_pn, roi_y_pn])
                self.threadpool.start(worker)
                while self.flag_update_original_video:
                    QtCore.QCoreApplication.processEvents()

                self.flag_update_original_video = True
                title = title + 'PN_'
                self.set_plain_text.emit(" Done")

            self.p_max = self.original_video.shape[0] - (2 * batch_size) - 1
            self.object_update_progressBar.setProgress(0)
            self.object_update_progressBar.setRange(self.p_max)

            if flag_FPN:
                self.set_new_text.emit("Start DRA + " + mode_FPN + '-->')
                if flag_power_normalization:
                    d_arg = {'video': self.original_video_pn, 'batchSize': batch_size, 'flag_GUI': True,
                             'instance': DifferentialRollingAverage, 'FPN_flag_GUI': True,
                             'gui_select_correction_axis': axis,
                             'object_update_progressBar': self.object_update_progressBar,
                             'mode_FPN': mode_FPN}
                else:
                    d_arg = {'video': self.original_video, 'batchSize': batch_size, 'flag_GUI': True,
                             'instance': DifferentialRollingAverage, 'FPN_flag_GUI': True,
                             'gui_select_correction_axis': axis,
                             'object_update_progressBar': self.object_update_progressBar,
                             'mode_FPN': mode_FPN}

                title = title + mode_FPN + '_'

            else:
                self.set_new_text.emit("Start DRA -->")
                if flag_power_normalization:
                    d_arg = {'video': self.original_video_pn, 'batchSize': batch_size, 'flag_GUI': True, 'mode_FPN': mode_FPN,
                             'instance': DifferentialRollingAverage, 'FPN_flag_GUI': False, 'gui_select_correction_axis': axis,
                             'object_update_progressBar': self.object_update_progressBar}
                else:
                    d_arg = {'video': self.original_video, 'batchSize': batch_size, 'flag_GUI': True, 'mode_FPN': mode_FPN,
                             'instance': DifferentialRollingAverage, 'FPN_flag_GUI': False, 'gui_select_correction_axis': axis,
                             'object_update_progressBar': self.object_update_progressBar}

            self.flag_thread_dra = True
            self.flag_update_dra = True
            self.startProgressBar(**d_arg)

            while self.flag_thread_dra:
                QtCore.QCoreApplication.processEvents()

            while self.flag_update_dra:
                QtCore.QCoreApplication.processEvents()

            self.set_plain_text.emit(" Done")

            title = title + 'DRA'

            return self.DRA_video


        else:
            self.msg_box = QtWidgets.QMessageBox()
            self.msg_box.setWindowTitle("Warning!")
            self.msg_box.setText("Please load one video!")
            self.msg_box.exec_()

