from PyQt5.QtWidgets import QWidget, QVBoxLayout, QDesktopWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MyPlottingWindow(QWidget):
    def __init__(self, calib_window, start_window, my_settings):
        super().__init__()

        self.calib_window = calib_window
        self.start_window = start_window
        self.my_settings = my_settings

        self.figure = Figure()
        self.figure.tight_layout()
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.setContentsMargins(0, 0, 0, 0)
        # layout.setSpacing(0)
        self.setLayout(layout)
        self.setWindowTitle("Calibration & Spectrum")

    def plot_graphs(self, out):
        title_font_size = 12
        label_font_size = 16

        ax = self.figure.add_subplot(211)

        # Plot for Resized filtered data
        ax.plot(out[1], out[2], label=self.start_window.translations[self.start_window.lang]['fig_opt'])
        ax.plot(out[3], out[4], label=self.start_window.translations[self.start_window.lang]['fig_ref'])
        ax.legend()
        ax.set_title(
            f"{self.start_window.translations[self.start_window.lang]['fig_resampled']} {self.calib_window.s_n_export}",
            fontsize=title_font_size)
        ax.set_ylabel(self.start_window.translations[self.start_window.lang]['fig_acc'], fontsize=label_font_size)
        ax.set_xlabel(self.start_window.translations[self.start_window.lang]['fig_time'], fontsize=label_font_size)
        ax.grid(True, which='both')
        ax.minorticks_on()

        # Plot for Power spectrum
        if self.my_settings.calib_do_spectrum:
            ax = self.figure.add_subplot(212)
            ax.plot(out[5], out[6], label=self.start_window.translations[self.start_window.lang]['fig_opt'])
            ax.plot(out[7], out[8], label=self.start_window.translations[self.start_window.lang]['fig_ref'])
            ax.legend()
            ax.set_title(
                f"{self.start_window.translations[self.start_window.lang]['fig_spektrum']} {self.calib_window.s_n_export}",
                fontsize=title_font_size)
            ax.set_ylabel(self.start_window.translations[self.start_window.lang]['fig_dens'], fontsize=label_font_size)
            ax.set_xlabel(self.start_window.translations[self.start_window.lang]['fig_freq'], fontsize=label_font_size)
            ax.grid(True, which='both')
            ax.minorticks_on()
            ax.set_xlim(self.my_settings.generator_sweep_start_freq,
                    self.my_settings.generator_sweep_stop_freq)
        self.canvas.draw()

        screen = QDesktopWidget().screenGeometry()
        self.resize(int(screen.width()/2.5), screen.height())
        self.move(0, 0)
        return self.width()

