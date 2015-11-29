import sys
import os
import itertools
import json
import struct
import ctypes
import socket

from django.db import models
from django.utils import timezone
import iguanaIR

DEFAULT_CARRIER_FREQUENCY = 38000

class ProntoCode(models.Model):
    device = models.CharField(max_length=60)
    button = models.CharField(max_length=60)
    pronto_code = models.TextField()

    def __unicode__(self):
        return "%s %s" % (self.device, self.button)

    class Meta:
        unique_together = (("device", "button"),)
        app_label = "irsignal"

class Config(models.Model):
    busy_start_time = models.DateTimeField(null=True, default=None)

    @classmethod
    def get(cls):
        configs = cls.objects.all()
        if len(configs) == 0:
            config = Config()
            config.save()
            return config

        assert len(configs) == 1
        return configs[0]

    class Meta:
        app_label = "irsignal"

#----------------------------------------------------------------------------
# High-level functions, classes, and exceptions:

class IRError(Exception):
    def __init__(self, message):
        # Some iguanaIR functions will set errno to indicate what went wrong.
        self.errno = ctypes.get_errno()
        if self.errno != 0:
            message += " (errno %s)" % self.errno
        super(IRError, self).__init__(message)

def send_button(device_name, button_name, repeat=1):
    """Send the signal for the given button to the given device."""
    carrier_frequency, signals = get_iguana_signals_for_button(
        device_name, button_name, repeat)
    send_iguana_signals(carrier_frequency, signals)

def record_button(device_name, button_name):
    """Record the signal for a button, saving it to disk for later use."""
    pronto_code = record_pronto_code()
    save_button(device_name, button_name, pronto_code)

def is_busy():
    config = Config.get()
    return (config.busy_start_time is not None and
        (timezone.now() - config.busy_start_time).total_seconds() < 5)

#----------------------------------------------------------------------------
# IR code storage functions:

def get_iguana_signals_for_button(device_name, button_name, repeat=1):
    """Get the iguana signal for a button on a device, retrieving it from
    cache if the device's buttons have been loaded in.

    Returns (carrier_sequence, signals).
    """
    # The pronto codes are stored as space/newline separated hexadecimal values.
    return pronto_code_to_iguana_signals(
        ProntoCode.objects.get(
            device=device_name, button=button_name).pronto_code,
        repeat)

def save_button(device_name, button_name, pronto_code):
    ProntoCode.objects.filter(device=device_name, button=button_name).delete()
    ProntoCode(
        device=device_name,
        button=button_name,
        pronto_code=pronto_code,
    ).save()

#----------------------------------------------------------------------------
# Pronto code functions:

def pronto_code_to_pronto_signals(pronto_code, repeat=1):
    parts = [int(part, 16) for part in pronto_code.split()]

    # The first value is always zero.  The second is an encoding of the carrier
    # frequency.  The third is the number of pairs in the non-repeating
    # sequence, and the second is the number of pairs in the repeating
    # sequence.  The pairs are a pulse value followed by a space value,
    # in terms of carrier frequency cycles.
    carrier_frequency = 1000000 / (parts[1] * 0.241246)
    carrier_frequency = int(round(carrier_frequency / 100)) * 100
    seq1_num_pairs = parts[2]
    seq2_num_pairs = parts[3]
    assert (seq1_num_pairs + seq2_num_pairs) * 2 == len(parts) - 4

    seq1_start_index = 4
    seq2_start_index = seq1_start_index + seq1_num_pairs * 2
    seq1 = parts[seq1_start_index:seq1_start_index + seq1_num_pairs * 2]
    seq2 = parts[seq2_start_index:seq2_start_index + seq2_num_pairs * 2]

    # Note that signals contain (pulse, space) pairs, but we discard the last
    # space.
    return carrier_frequency, (seq1 + seq2 * repeat)[:-1]

def pronto_signals_to_pronto_code(carrier_frequency, seq1, seq2):
    assert len(seq1) % 2 == 0 and len(seq2) % 2 == 0
    encoded_carrier_frequency = int(
        round(1000000 / (0.241246 * carrier_frequency)))
    return " ".join("%04X" % value
        for value in itertools.chain(
            (0, encoded_carrier_frequency, len(seq1) / 2, len(seq2) / 2),
            seq1, seq2))

def nec_code_to_pronto_code(device_address, key_code):
    # An NEC code uses a carrier frequency of 38kHz and consists of:
    # - 9ms burst pulse (342), 4ms space (152)
    # - 8-bit device address
    # - 8-bit logical inverse of device address
    # - 8-bit key code
    # - 8-bit logical inverse of the key_code
    # - 562.5us pulse (~22)
    # - 40ms space (1520)
    # Followed by an optional number of repeating:
    # - 9ms pulse (342)
    # - 2.25ms space (86)
    # - 562.5us pulse (~22)
    # - 96ms space (3648)
    #
    # A 0 bit is encoded as a 562.5us (21) pulse and 562.5us (21) space.
    # A 1 bit is encoded as a 562.5us (21) pulse and 1687.5us (64) space.
    # The data bytes are sent least significant bit first.
    seq1 = [342, 152]
    seq1.extend(nec_signal_for_byte(device_address))
    seq1.extend(nec_signal_for_byte(~device_address & 0xf))
    seq1.extend(nec_signal_for_byte(key_code))
    seq1.extend(nec_signal_for_byte(~key_code & 0xf))
    seq1.extend((22, 1520))

    seq2 = [342, 86, 22, 3648]
    return pronto_signals_to_pronto_code(38000, seq1, seq2)

def philips_rc5_to_pronto_code(device_address, key_code):
    # A Philips RC5 code uses a carrier frequency of 36kHz and consists of
    # 14 bits in a row:
    # - 2 start bits, but 1's
    # - 1 toggle bit, that remains constant when the button is held down and
    #   changes when pressed and released repeatedly
    # - 5 bits for the device address
    # - 6 bits for the command
    #
    # A 0 bit is encoded as an 889us (32) pulse and an 889us (32) space.
    # A 1 bit is encoded as an 889us (32) space and an 889us (32) pulse.
    # The data bytes are sent most significant bit first.
    # The whole sequence is followed by an 89.108ms (3208) space and may be
    # repeated.
    pulses = [1, # first 1 start bit, without the leading space
        0, 1, # second 1 start bit
        1, 0] # toggle bit of 0
    pulses.extend(
        encode_bits_as_signal(device_address, range(4, -1, -1), (1, 0), (0, 1)))
    pulses.extend(
        encode_bits_as_signal(key_code, range(5, -1, -1), (1, 0), (0, 1)))

    seq1 = []
    seq2 = [count * 32 for count in occurrence_counts(pulses)]

    # Add the space at the end, ensuring we have pairs of (pulse, space) values.
    if len(seq2) % 2 == 1:
        seq2.append(3208)
    else:
        seq2[-1] += 3208

    return pronto_signals_to_pronto_code(36000, seq1, seq2)

def occurrence_counts(seq):
    last_value = seq[0]
    count = 1
    for value in seq[1:]:
        if last_value == value:
            count += 1
        else:
            yield count
            last_value = value
            count = 1

    yield count

def nec_signal_for_byte(value):
    return encode_bits_as_signal(value, range(8), (21, 21), (21, 64))

def encode_bits_as_signal(value, bit_indices, false_seq, true_seq):
    signals = []
    for i in bit_indices:
        signals.extend(true_seq if (value & (1 << i)) else false_seq)
    return signals

#----------------------------------------------------------------------------
# Pronto/Iguana conversion functions:

def pronto_code_to_iguana_signals(pronto_code, repeat):
    carrier_frequency, signals = pronto_code_to_pronto_signals(
        pronto_code, repeat)
    return (carrier_frequency,
        pronto_signals_to_iguana_signals(carrier_frequency, signals))

def pronto_signals_to_iguana_signals(carrier_frequency, signals):
    """Convert the pronto format into iguana format, where the pulses and spaces
    are represented in number of microseconds.
    """
    return [carrier_cycles_to_microseconds(carrier_frequency, signal) | command
        for signal, command in
            zip(signals, itertools.cycle((iguanaIR.IG_PULSE_BIT, 0)))]

def carrier_cycles_to_microseconds(carrier_frequency, signal):
    return int(round(float(signal * 1000000) / carrier_frequency))

def iguana_signals_to_iguana_file(signals):
    """Return a sequence of iguana signals in a format that can be sent by
    igclient.  Note that you must have set the proper carrier sequence
    beforehand.
    """
    lines = []
    for signal in signals:
        signal_type = ("pulse" if signal & iguanaIR.IG_PULSE_BIT else "space")
        lines.append("%s %s\n" % (signal_type, signal & iguanaIR.IG_PULSE_MASK))
    return "".join(lines)

def iguana_signals_to_pronto_signals(carrier_frequency, signals):
    return [int(round((microseconds & iguanaIR.IG_PULSE_MASK) *
            carrier_frequency / 1000000.0))
        for microseconds in signals]

#----------------------------------------------------------------------------
# Recording functions:

def record_pronto_code():
    carrier_frequency, iguana_signals = record_iguana_signals(
        keep_end_space=True)
    pronto_signals = iguana_signals_to_pronto_signals(
        carrier_frequency, iguana_signals)
    return pronto_signals_to_pronto_code(carrier_frequency, (), pronto_signals)

def record_iguana_signals(keep_end_space=False):
    set_iguana_carrier_frequency(DEFAULT_CARRIER_FREQUENCY)
    iguana_signals = receive_iguana_signals(keep_end_space=True)
    iguana_signals = truncate_iguana_signals_at_gap(
        iguana_signals, keep_end_space=True)
    carrier_frequency = guess_carrier_frequency(iguana_signals)
    return carrier_frequency, iguana_signals

def truncate_iguana_signals_at_gap(signals, keep_end_space=False):
    # Look at all the unique space values.
    spaces = set(signals[1::2])

    # Find the gap by finding first very large jump in space sizes.
    sorted_spaces = tuple(sorted(spaces))
    large_space = None
    for i, space in enumerate(sorted_spaces):
        if i == 0:
            continue

        prev_space = sorted_spaces[i - 1]
        if (space - prev_space) / float(prev_space) > 10:
            large_space = space
            break

    if large_space is None:
        return signals[:]

    truncated_signals = []
    for i, signal in enumerate(signals):
        if i % 2 == 1 and signal >= large_space:
            break
        truncated_signals.append(signal)

    if keep_end_space:
        truncated_signals.append(large_space)

    return truncated_signals

def guess_carrier_frequency(signals):
    # TODO: This always chooses the highest frequency we look for.  So, we punt
    #       and choose the default frequency.
    return DEFAULT_CARRIER_FREQUENCY

    # Carrier frequencies are typically 33-40 kHz or 50-60 KHz, with 38 KHz
    # being the most common.
    best_error = None
    best_carrier_frequency = None

    # Look at the sum of the roundoff errors when converting to cycles for
    # various carrier frequencies.
    for carrier_frequency in itertools.chain(
            (38000,),
            range(33000, 38000, 1000),
            range(39000, 41000, 1000),
            range(50000, 61000, 1000)):
        error = sum(error_with_carrier_frequency(
                carrier_frequency, signal & iguanaIR.IG_PULSE_MASK)
            for signal in signals)
        if best_error is None or best_error > error:
            best_error = error
            best_carrier_frequency = carrier_frequency

    return carrier_frequency

def error_with_carrier_frequency(carrier_frequency, original_microseconds):
    cycles = int(round(original_microseconds * carrier_frequency / 1000000.0))
    microseconds = 1000000.0 * cycles / carrier_frequency
    return abs(original_microseconds - microseconds)

#----------------------------------------------------------------------------
# Iguana device functions:

def mark_as_busy(is_busy):
    config = Config.get()
    config.busy_start_time = (timezone.now() if is_busy else None)
    config.save()

def connect_to_iguana():
    conn = iguanaIR.connect("0")
    if not conn or conn == -1:
        raise IRError("Could not connect to the iguanaIR device")
    return conn

def send_iguana_signals(carrier_frequency, signals):
    """Given a carrier frequency and signals in iguana format (as returned by
    get_iguana_signals_for_button), send them using the device.
    """
    mark_as_busy(True)
    try:
        conn = connect_to_iguana()
        set_iguana_carrier_frequency(carrier_frequency, conn)
        send_iguana_request(conn, iguanaIR.IG_DEV_SEND,
            [signal | command for signal, command in zip(
                signals, itertools.cycle((iguanaIR.IG_PULSE_BIT, 0)))])
        iguanaIR.close(conn)
    finally:
        mark_as_busy(False)

_last_carrier_frequency = None
def set_iguana_carrier_frequency(carrier_frequency, conn=None):
    global _last_carrier_frequency
    if (_last_carrier_frequency is not None and
            _last_carrier_frequency == carrier_frequency):
        return

    _last_carrier_frequency = carrier_frequency

    conn_was_none = conn is None
    if conn is None:
        conn = connect_to_iguana()
    send_iguana_request(
        conn, iguanaIR.IG_DEV_SETCARRIER, [socket.htonl(carrier_frequency)])
    if conn_was_none:
        iguanaIR.close(conn)

def send_iguana_request(
        conn, command_type, command_data=None, wait_for_response=True):
    if command_data is not None:
        request = iguanaIR.createRequest(
            command_type,
            "".join(struct.pack("I", signal) for signal in command_data))
    else:
        request = iguanaIR.createRequest(command_type)
    result = iguanaIR.writeRequest(request, conn)

    if wait_for_response:
        response = iguanaIR.readResponse(conn, 1000)
        if iguanaIR.responseIsError(response):
            raise IRError("An error occurred while sending an IR signal")

def receive_iguana_signals(keep_end_space=False):
    conn = connect_to_iguana()

    # Turn on the IR receiver.
    send_iguana_request(conn, iguanaIR.IG_DEV_RECVON, wait_for_response=False)

    # collect signals until we have a huge gap of 1 second
    signals = []
    current_type = 0
    current_length = 0
    while True:
        packet = iguanaIR.readResponse(conn, 1000)
        if packet is None:
            raise IRError("No packet received in the last second")
        data = iguanaIR.removeData(packet)

        for signal in struct.unpack('I' * (len(data) / 4), data):
            if signal & iguanaIR.IG_PULSE_BIT != current_type:
                if current_length > iguanaIR.IG_PULSE_MASK:
                    current_length = iguanaIR.IG_PULSE_MASK
                signals.append(current_type | current_length)

                # prepare for the next pass
                current_type = signal & iguanaIR.IG_PULSE_BIT
                current_length = 0

            # stop when we've collected a full signal
            current_length += signal & iguanaIR.IG_PULSE_MASK
        if current_length > 1000000 and len(signals) != 0:
            break

    iguanaIR.close(conn)

    # Make sure we start with a pulse, not a space.
    if not (signals[0] & iguanaIR.IG_PULSE_BIT):
        signals = signals[1:]

    # Make sure we end with a pulse, not a space.
    if not keep_end_space and len(signals) % 2 == 0:
        signals = signals[:-1]
    elif keep_end_space and len(signals) % 2 == 1:
        signals.append(signals[-2])

    return signals

def exit_with_usage():
    usage = (
        "irsignal.py <device_name> <button_name>"
        " [nec|rc5 <device_address> <key_code>]\n"
        "If an NEC or RC5 code is given, adds it to the database for the given"
        " device and button names.  Otherwise, if the code exists it sends it,"
        " and if it does not exist it records and saves it."
        )
    sys.exit(usage)

