#!/usr/bin/env python
"""This script watches a given directory for new pdf files
   and renames and moves files according to a set of rules"""

#dependencies: watchdog, pyyaml, pdftotext (cmd line from poppler)

import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys
import os
from argparse import ArgumentParser
import yaml
import subprocess
import shutil
import logging
import re
import datetime

#TODO   - default date format
#       - fix pylint errors
#       - change remaining print statements to logger

#FUTURE
#       - adjust mac colour labels

#borrowed heavily from here: http://virantha.com/2013/04/20/python-auto-sort-of-ocred-pdfs/
#could look at ocr from https://github.com/virantha/pypdfocr
#idea from here - https://github.com/joeworkman/paperless

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def setup_logging(logger_):
    handler = logging.FileHandler('pyscanrename.log')
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_formatter = logging.Formatter('%(levelname)s - %(message)s')
    stream_handler.setFormatter(stream_formatter)

    logger_.addHandler(handler)
    logger_.addHandler(stream_handler)

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, pdfsearcher):
        FileSystemEventHandler.__init__(self)
        self.pdfsearcher = pdfsearcher

    def check_for_new_pdf(self, ev_path):
        if ev_path.endswith(".pdf"):
            #if not ev_path.endswith("_OCR.pdf"):
            if os.path.exists(ev_path):
                print("Analyzing file %s" % ev_path)
                pdf = self.pdfsearcher
                pdf.process_new_pdf(ev_path)

    def on_created(self, event):
        print("on_created: {}".format(event.src_path))
        self.check_for_new_pdf(event.src_path)

    def on_moved(self, event):
        print("on_moved: %s" % event.src_path)
        self.check_for_new_pdf(event.dest_path)

    def on_modified(self, event):
        print("on_modified: %s" % event.src_path)
        self.check_for_new_pdf(event.src_path)

    def on_deleted(self, event):
        print("on_deleted: %s" % event.src_path)

def consult_pdftotext(filename):
    '''
    Runs pdftotext to extract text of pages 1..3.
    Returns the count of characters received.

    `filename`: Name of PDF file to be analyzed.
    '''
    logger.debug("Running pdftotext on file %s", filename)
    # don't forget that final hyphen to say, write to stdout!!
    cmd_args = ["pdftotext", "-enc", "UTF-8", "-f", "1", "-l", "2", filename, "-"]
    pdf_pipe = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        std_out, std_err = pdf_pipe.communicate(timeout=15)
    except TimeoutExpired:
        pdf_pipe.kill()
        std_out, std_err = pdf_pipe.communicate()
    std_out = std_out.decode('UTF-8')
    std_err = std_err.decode('UTF-8')
    return std_out

class DateSearch():
    def __init__(self, date_locale):
        self.date_locale = date_locale

    SEP_NOSPACE = r'\.\/\-\,'
    SEP = r'\. \/\-\,'
    DAY = r'(\d{1,2})'
    MONTH = r'([a-zA-Z]{3,15})'
    YEAR = r'(\d{4}|\d{2})'
    END_DATE = r'(\s|$)'
    date1 = re.compile(r'(\d{1,2})[\.\/\-\,]+(\d{1,2})[\.\/\-\,]+(\d{4}|\d{2})')
    date2 = re.compile(r'([a-zA-Z]{3,15})[\. \/\-\,]{0,3}(\d{1,2})[\. \/\-\,]{1,3}(\d{4}|\d{2})\s')
    date3 = re.compile(r'(\d{1,2})[\. \/\-\,]{0,3}([a-zA-Z]{3,15})[\. \/\-\,]{0,3}(\d{4}|\d{2})')
    date4 = re.compile(r'([a-zA-Z]{3,15})[\. \/\-\,]{0,3}(\d{4}|\d{2})')

    def valid_day(self, num):
        day = int(num)
        if day <= 31:
            return day
        else:
            return False

    #todo - support other language formats
    def valid_month(self, month):
        if month.isnumeric():
            month = int(month)
            if month <= 12:
                return month
            else:
                return False

        month = month.lower()
        if month == "jan" or month == "january":
            return 1
        elif month == "feb" or month == "february":
            return 2
        elif month == "mar" or month == "march":
            return 3
        elif month == "apr" or month == "april":
            return 4
        elif month == "may" or month == "may":
            return 5
        elif month == "jun" or month == "june":
            return 6
        elif month == "jul" or month == "july":
            return 7
        elif month == "aug" or month == "august":
            return 8
        elif month == "sep" or month == "september":
            return 9
        elif month == "oct" or month == "october":
            return 10
        elif month == "nov" or month == "november":
            return 11
        elif month == "dec" or month == "december":
            return 12
        return False

    def valid_year(self, num):
        year = int(num)
        now = datetime.date.today().year

        if year < 100:
            #transform 2 digit date into 4 digit date
            now_two_digit_year = now - 2000
            # In the 1900s? Need to add 1900. Else add 2000
            if year > now_two_digit_year:
                year += 1900
            else:
                year += 2000

        # No file can have a date prior to 1970
        if year > 1970 and year <= now:
            return year
        else:
            return False

    def date_search(self, text):
        date = None
        month = None
        day = None
        year = None
        match1 = self.date1.search(text)
        match2 = self.date2.search(text)
        match3 = self.date3.search(text)
        match4 = self.date4.search(text)
        match = ''
        if match1:
            # US:   12-29-2011
            # Euro: 29-12-2011
            match = match1.group(0)
            year = self.valid_year(match1.group(3))
            if self.date_locale == 'us':
                day = self.valid_day(match1.group(2))
                month = self.valid_month(match1.group(1))
            else:
                day = self.valid_day(match1.group(1))
                month = self.valid_month(match1.group(2))
        elif match2:
            # December 29, 2011
            match = match2.group(0)
            day = self.valid_day(match2.group(2))
            year = self.valid_year(match2.group(3))
            month = self.valid_month(match2.group(1))
        elif match3:
            # 29 December 2011
            match = match3.group(0)
            day = self.valid_day(match3.group(1))
            month = self.valid_month(match3.group(2))
            year = self.valid_year(match3.group(3))
        elif match4:
            # December 2011
            match = match4.group(0)
            year = self.valid_year(match4.group(2))
            month = self.valid_month(match4.group(1))
            day = 1

        if month and day and year:
            logger.debug('Basing the date off the discovered string %s', match)
            date = datetime.date(year, month, day)
        else:
            logger.warning('WARNING: The discovered date string does not validate: %s', match)

        return date

class PdfSearcher(object):
    def __init__(self, output, default, simulate, date_locale, prompt, default_date_format):
        self.pdf_text = ""
        self.output_folder = output
        self.default_folder = default
        self.simulate = simulate
        self.prompt = prompt
        self.rules = []
        self.filename = ''
        self.datesearch = DateSearch(date_locale)
        self.date_filter = re.compile(r'<date([=\%YyMmDd-]*)>')
        self.future_date_filter = re.compile(r'<date=.*[^\%YyMmDd-]+.*>')
        self.default_date_format = default_date_format

    def process_new_pdf(self, filename):
        self.filename = filename
        logger.info('')
        logger.info('Testing file: %s', filename)
        self.read_pdf_first_page(filename)

        self.process_date()

        for rule in self.rules:
            if self.process_rule(rule):
                return True
        logger.warning('No rules matched the file')
        logger.debug('File text was: %s', self.pdf_text)
        return False

    def read_pdf_first_page(self, filename):
        text = consult_pdftotext(filename)
        self.pdf_text = text
        return

    def add_rule(self, rule):
        # Used externally to add in the keywords/folders
        logger.debug('New rule: ')
        logger.debug(rule)
        if not 'description' in rule:
            logger.warning('This rule has no description. Each rule must have a description.')
            return False
        if not 'content' in rule:
            logger.warning(
                'This rule has no content. Currently each rule must have a content field.')
            return False
        if type(rule['content']) != 'string':
            rule['content'] = str(rule['content'])
        if not 'filename' in rule and not 'destination' in rule:
            logger.warning('This rule has no output. Each rule must provide a '
                           'new filename or a destination to copy to')
            return False
        if self.future_date_filter.search(rule['filename']):
            logger.warning('This date format is not supported. This rule will be ignored.')
            return True #this lets execution continue but we do not add the rule

        self.rules.append(rule)
        return True

    def process_date(self):
        #look for a date in the file to use in file renaming
        date = self.datesearch.date_search(self.pdf_text)
        if date:
            self.date = date
            logger.info('Date for this file was set to: %s', date.isoformat())
        else:
            self.date = None
            logger.info('No date was found for this file')

    def apply_date(self, basename, rule):
        match = self.date_filter.search(basename)
        if match:
            if not self.date:
                logger.error('No date was found, but the filename requires a date')
                raise TypeError
            if rule['adjust_month']:
                self.date = self.date.replace(month=self.date.month + int(rule['adjust_month']))
            logger.debug(match.groups())
            if len(match.group(1)) == 0:
                dateformat = self.default_date_format
            elif match.group(1)[0] == '=':
                dateformat = match.group(1)[1:]
            else:
                dateformat = match.group(1)
            basename = (basename[:match.start()] +
                        self.date.strftime(dateformat) +
                        basename[match.end():])
            logger.debug('New basename after date substitution %s', basename)
        return basename

    def process_rule(self, rule):
        dirname, basename = os.path.split(self.filename)

        logger.debug('')
        logger.debug('Processing rule: %s against file: %s', rule['description'], basename)
        logger.debug('Looking for: %s', rule['content'])
        if rule['content'] in self.pdf_text:
            logger.debug('Matched rule')
            if 'filename' in rule:
                dest_base_name = rule['filename']
                dest_base_name = self.apply_date(dest_base_name, rule)
                dest_base_name = self.check_ending(dest_base_name, basename)
            else:
                dest_base_name = basename

            if 'destination' in rule:
                dest_dir = rule['destination']
            else:
                dest_dir = self.default_folder
            dest_dir = os.path.join(self.output_folder, dest_dir)

            self.rename_and_move_file(dest_base_name, dest_dir)

            return True
        return False

    def rename_and_move_file(self, dest_base_name, dest_dir):
        dest = os.path.join(dest_dir, dest_base_name)
        base, ext = os.path.splitext(dest_base_name)

        #rename if necessary
        count = 0
        while os.path.exists(dest):
            count += 1
            dest = os.path.join(dest_dir, '%s-%d%s' % (base, count, ext))

        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            logger.debug("Making path %s", dest_dir)

        if self.simulate:
            logger.info('Would have moved %s to %s', self.filename, dest)
        elif self.prompt:
            print('Will move {} to {}'.format(self.filename, dest))
            resp = input('Proceed? [Y/n]')
            if resp == "" or resp == "Y" or resp == "y":
                shutil.move(self.filename, dest)
        else:
            logger.info('Moved %s to %s', self.filename, dest)
            shutil.move(self.filename, dest)

    def check_ending(self, newname, oldname):
        new_base, new_ext = os.path.splitext(newname)
        old_base, old_ext = os.path.splitext(oldname)

        if new_ext != old_ext:
            newname = newname + old_ext
        return newname

class ScanEver(object):

    def __init__(self):
        self.maxlength = 500
        self.watch_folder = None
        self.output_folder = None
        self.default_folder = None
        self.searcher = None

    def get_options(self, argv):
        usage = 'ScanEver '
        parser = ArgumentParser(usage)

        parser.add_argument('-d', '--debug', action='store_true',
                            default=False, dest='debug', help='Turn on debugging')
        parser.add_argument('-s', '--simulate', action='store_true',
                            default=False, dest='simulate',
                            help='Simulate results but don\'t modify anything')
        parser.add_argument('-p', '--prompt', action='store_true',
                            default=False, dest='prompt',
                            help='Prompt for an action after each file processed')
        parser.add_argument('-l', '--locale', action='store',
                            default='us', dest='locale',
                            help='Locale for date strings. Defaults to \'us\'')

        args = parser.parse_args(argv)

        if args.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug('Logging at debug level')

        if args.simulate:
            logger.info('Simulate is on. No renaming will occur')

        config_file = "config.yaml"
        try:
            fstream = open(config_file, "r")
        except FileNotFoundError:
            logger.error('Could not open configuration file: %s', config_file)
            exit(-1)

        myopts = yaml.load(fstream)

        success = True
        self.watch_folder = myopts['watch_folder']
        self.output_folder = myopts['output_folder']
        self.default_folder = os.path.join(self.output_folder, myopts['default_folder'])

        if myopts['default_date_format']:
            self.default_date_format = myopts['default_date_format']
        else:
            self.default_date_format = '%Y-%m-%d'
        logger.debug('Default date format is: %s', self.default_date_format)

        #check folders exist
        if not os.path.isdir(self.watch_folder):
            logger.error('The watch folder does not exist: %s', self.watch_folder)
            success = False
        if not os.path.isdir(self.output_folder):
            logger.error('The output folder does not exist: %s', self.output_folder)
            success = False
        if not os.path.isdir(self.default_folder):
            logger.error('The default folder does not exist: %s', self.default_folder)
            success = False

        #create our main object
        self.searcher = PdfSearcher(self.output_folder, self.default_folder,
                                    args.simulate, args.locale, args.prompt,
                                    self.default_date_format)

        #and load in rules
        for strings in myopts["rules"]:
            success = success and self.searcher.add_rule(strings)
        if not success:
            exit(-1)

    def monitor(self):
        #try existing pdf files
        pdf_files = [f for f in os.listdir(self.watch_folder)
                     if os.path.isfile(os.path.join(self.watch_folder, f))
                     and os.path.splitext(f)[1].lower() == '.pdf']

        logger.debug('Initial files to try: %s', pdf_files)
        for filename in pdf_files:
            self.searcher.process_new_pdf(os.path.join(self.watch_folder, filename))

        if len(pdf_files) > 0:
            logger.info('Done with initial files. Now monitoring the watch folder')

        while True:
            event_handler = ChangeHandler(self.searcher)
            observer = Observer()
            observer.schedule(event_handler, os.path.abspath(self.watch_folder))
            observer.start()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
                exit(-1)
            observer.join()

    def start(self, argv):
        # Read the command line options
        self.get_options(argv)
        self.monitor()

if __name__ == '__main__':
    setup_logging(logger)
    scanner = ScanEver()
    scanner.start(sys.argv[1:])
    