#BPM DDC simulator
#Copyright (C) 2013  Aylons Hazzud
#
#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along
#with this program; if not, write to the Free Software Foundation, Inc.,
#51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from gnuradio import gr
from gnuradio import blocks, analog, filter
import scipy, pylab

# Sample rate, in SPS
samp_rate = 130e6

# Limit the number of samples to N
N = int(130e3*2)
head = blocks.head(gr.sizeof_float, N)

##Simulates the input from the ADC. For simplifying, this is a float, may be
#changed to fixed point in the future, so we can better simulate
class adc_signal(gr.hier_block2):
    def __init__(self, samp_rate):
        gr.hier_block2.__init__(self, "BPM Signal from ADC",
                              gr.io_signature(0,0,0),#no input, this is a source
                              gr.io_signature(1,1,gr.sizeof_float))

        carrier = analog.sig_source_f(samp_rate,   analog.GR_COS_WAVE, 20e6, 1, 0)
        modulating = analog.sig_source_f(samp_rate, analog.GR_SIN_WAVE, 2e3,  0.05, 0.975)
        mixer = blocks.multiply_ff(1)

        self.connect(carrier, (mixer,0))
        self.connect(modulating, (mixer,1))
        self.connect(mixer,self)

class ddc_mixer(gr.hier_block2):
    def __init__(self, samp_rate, center_freq):
        gr.hier_block2.__init__(self, "Mixer for downconversion",
                                gr.io_signature(1,1,gr.sizeof_float),
                                gr.io_signature(2,2,gr.sizeof_float))

        cosine = analog.sig_source_f(samp_rate, analog.GR_COS_WAVE, center_freq, 1, 0)
        sine   = analog.sig_source_f(samp_rate, analog.GR_SIN_WAVE, center_freq, 1, 0)

        mixer_I = blocks.multiply_ff(1)
        mixer_Q = blocks.multiply_ff(1)

        self.connect(self,   (mixer_I,0))
        self.connect(cosine, (mixer_I,1))

        self.connect(self, (mixer_Q,0))
        self.connect(sine, (mixer_Q,1))

        self.connect(mixer_I, (self,0))
        self.connect(mixer_Q, (self,1))

class float_cordic(gr.hier_block2):
    def __init__(self):
        gr.hier_block2.__init__(self, "CORDIC from I,Q floats",
                                gr.io_signature(2,2,gr.sizeof_float),
                                gr.io_signature(2,2,gr.sizeof_float))

        ftc = blocks.float_to_complex()
        mag = blocks.complex_to_mag()
        arg = blocks.complex_to_arg()

        self.connect((self,0), (ftc,0))
        self.connect((self,1), (ftc,1))
        self.connect(ftc,mag,(self,0))
        self.connect(ftc,arg,(self,1))


tb = gr.top_block()

source= adc_signal(samp_rate)

#Ddc mixer
mixer = ddc_mixer(samp_rate, 20e6)

#Decimation filter. Both must have the same taps, so, calculate it once
taps = filter.firdes.low_pass_2(1, samp_rate, 5e3, 3e3, 60,
                                filter.firdes.WIN_BLACKMAN_HARRIS)
filter_I = filter.pfb_decimator_ccf(int(1e3), taps, 0)
filter_Q = filter.pfb_decimator_ccf(int(1e3), taps, 0)

#now, calculate Magnitude and Argument
cordic = float_cordic()

#output the result
sink = blocks.vector_sink_f()

tb.connect(source, head)
tb.connect(head, ddc_mixer)
tb.connect((ddc_mixer,0), filter_I)
tb.connect((ddc_mixer,1), filter_Q)
tb.connect(filter_I, (cordic,0))
tb.connect(filter_Q, (cordic,1))
tb.connect((cordic,1),sink)

tb.run()

## Here start the analysis

#Addint source plot
data = scipy.array(sink.data())
time = scipy.arange(0,N/samp_rate,2/samp_rate)
fig = pylab.figure(1)
sp1 = fig.add_subplot(1,1,1)
sp1.plot(time[0:N],data[0:N:2])

pylab.show()