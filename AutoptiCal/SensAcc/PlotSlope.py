from PyQt5.QtWidgets import QWidget, QVBoxLayout, QDesktopWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class PlotSlope(QWidget):
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
        self.setWindowTitle("Slope")

    def plot_graphs(self, out):
        title_font_size = 12
        label_font_size = 16

        ax = self.figure.add_subplot(211)

        ax.plot(out[0], out[3], label='WL1')
        ax.plot(out[0], out[2], color='red',
                label=f'slope*10e6 = {out[1]}')
        ax.set_xlabel(self.start_window.translations[self.start_window.lang]['Index'], fontsize=label_font_size)
        ax.set_ylabel(self.start_window.translations[self.start_window.lang]['slope_y'], fontsize=label_font_size)
        ax.grid(True, which='both')
        ax.minorticks_on()
        ax.set_title("WL1")
        ax.legend()
        if len(out) > 4:
            ax = self.figure.add_subplot(212)
            ax.plot(out[0], out[6], label='WL2')
            ax.plot(out[0], out[5], color='red',
                    label=f'slope*10e6 = {out[4]}')
            ax.set_xlabel(self.start_window.translations[self.start_window.lang]['Index'], fontsize=label_font_size)
            ax.set_ylabel(self.start_window.translations[self.start_window.lang]['slope_y'], fontsize=label_font_size)
            ax.set_title("WL2")
            ax.legend()
            ax.grid(True, which='both')
        self.canvas.draw()

        screen = QDesktopWidget().screenGeometry()
        self.resize(int(screen.width() / 2.5), screen.height())
        self.move(0, 0)
