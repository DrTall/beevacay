#!/usr/bin/python
"""


See the README file for details on how the road matricies are updated.
"""


import re
import json
from datetime import (date, datetime, timedelta, time)
import requests
import collections
import logging

import config_pb2

import secrets
import beelib

from google.protobuf import text_format

def epoch_time(date):
  """Seriously this is the best way to do this???"""
  return int((date - datetime(1970,1,1)).total_seconds())

TODAY = epoch_time(datetime.today())
#TODAY = epoch_time(datetime.combine(date.today(), time(hour=17)))
ONE_DAY = timedelta(days=1).total_seconds()
HORIZON = TODAY + 7 * ONE_DAY

# y, m, w, d, h
RUNITS_TIMEDELTAS = {
    'y': timedelta(weeks=52),
    'm': timedelta(weeks=4),
    'w': timedelta(weeks=1),
    'd': timedelta(days=1),
    'h': timedelta(hours=1),
    }

def mod(username, goalname, road):
  beeminder_url = (
            'https://www.beeminder.com/api/v1/users/' +
            '%(username)s/goals/%(goalname)s.json' %
            {'username': username, 'goalname':goalname})
  payload = {'auth_token':secrets.BEEMINDER_AUTH_TOKEN, 'roadall': json.dumps(road)}
  r = requests.put(beeminder_url, data=payload)

  print r.status_code
  print r.content

def get_roadall(username, goalname):
  beeminder_url = (
            'https://www.beeminder.com/api/v1/users/' +
            '%(username)s/goals/%(goalname)s.json' %
            {'username': username, 'goalname':goalname})
  r = requests.get(beeminder_url + "?auth_token=" + secrets.BEEMINDER_AUTH_TOKEN)
  if r.status_code == 200:
    data = json.loads(r.content)
    return data
  print 'Error fetching %s/%s: %s' % (username, goalname, r.content)
  return None

def get_config(path):
  with open(path) as f:
    result = config_pb2.BeevacayConfig()
    text_format.Merge(f.read(), result)
    return result

Brick = collections.namedtuple('Brick', ['date', 'total', 'rate'])

# total_handling: A VacationPattern.TotalHandling
VacationSegment = collections.namedtuple('VacationSegment', ['start', 'end', 'rate', 'total_handling'])

def compress_road(road):
  """Removes redundant road matrix entries.
  Args:
    road: A list of Bricks, where none are (-,t,m).
  Returns:
    A copy of road with the following adjustments:
      * All bricks with the same date will be removed except the first.
      * All bricks rate-bricks followed by another identical rate will be
        removed.
  """
  logging.debug("compress_road(%s)", road)
  result = []
  last_brick = None
  for brick in road[1:]:
    if last_brick:
      if last_brick.date == brick.date:
        if brick.rate is not None:
          logging.debug(
              "Discarding additional rate brick for date: %s (already have %s)",
              brick, last_brick)
          continue
        if brick.total is not None:
          logging.debug("Discarding previous total brick for date: %s "
                        "(using %s instead)", last_brick, brick)
          del result[-1]
      elif last_brick.rate is not None and last_brick.rate == brick.rate:
        logging.debug(
            "Discarding brick with identical rate: %s (using %s instead)",
            last_brick, brick)
        del result[-1]
    result.append(brick)
    last_brick = brick
  result = [road[0]] + result
  logging.debug("Compressed road: %s", result)
  return result

def insert_rah(road, rah):
  """Math is really annoying.

  The Beeminder API won't accept edits which make the road easier before the
  akrasia horizon, no matter how slight. When you edit the road dial, it
  automatically inserts a brick segment to maintain the pre-horizon road.
  This function does the same to try to make the edits via the API succeed
  all the time. Really this is a hack, and probably indicates there is some
  kind of timezone or rounding error going on somewhere.

  Args:
    road: A list of Bricks, where none are (-,t,m) and runits are d.
    rah: Road value at the akrasia horizon (today plus one week).
  Result:
    Road with rah inserted.
  """
  logging.debug("insert_rah(%s, %s)", road, rah)
  for insert_index, brick in enumerate(road):
    if brick.date > HORIZON:
      break
  else:
    logging.debug("Looks like this goal exists entirely within the horizon.")
    return road

  rah_brick = Brick(HORIZON, rah, None)
  logging.debug("Inserting a new brick %s at position %s.",
                rah_brick, insert_index)
  return (road[:insert_index] +
          [rah_brick] +
          road[insert_index:])
  

def apply_vacation_segment(road, runits, vacation_segment):
  """Modifies road to include vacation_segment.

  See README (Gory details of road splitting) for details.

  Args:
    road: A list of Bricks, where none are (-,t,m) and runits are d.
    runits: A string from RUNITS_TIMEDELTAS
    vacation_segment: A VacationSegment.
  Returns:
    A copy of road with vacation_segment inserted.
  """
  logging.debug("apply_vacation_segment(%s, %s)", road, vacation_segment)
  # Validate our assumptions about the road before we start tearing it up.
  assert road[0].date is not None and road[0].total is not None
  assert all(brick.date is not None for brick in road)
  rate_seconds = RUNITS_TIMEDELTAS[runits].total_seconds()

  if vacation_segment.end < road[0].date:
    logging.debug("This goal is newer than the vacation! Nothing to do.")
    return road
  if vacation_segment.start < road[0].date:
    logging.debug("This vacation starts before the goal but still overlaps. "
                  "Trimming vacation_segment.start from %s to %s",
                  vacation_segment.start, road[0].date)
    vacation_segment = vacation_segment._replace(start=road[0].date)

  result = []
  # A (d,t,-) brick tracking the cummulative total of the previous brick, even
  # if that brick happens to be a (d,-,m) brick.
  previous_metabrick = None
  for index, next_brick in enumerate(road):
    logging.debug("Walking the YBR to (%s, %s) with previous_metabrick=%s",
                  index, next_brick, previous_metabrick)
    if previous_metabrick is None:
      # Guaranteed to be (d,t,-) by the API.
      previous_metabrick = next_brick
      result.append(next_brick)
      continue

    if next_brick.date <= vacation_segment.start:
      # Haven't found the brick to edit yet, so just keep previous_metabrick
      # up to date.
      if next_brick.total is not None:
        previous_metabrick = next_brick
      else:
        previous_metabrick = Brick(
            next_brick.date,
            previous_metabrick.total +
            (next_brick.date - previous_metabrick.date) / (rate_seconds) * next_brick.rate,
            None)
      result.append(next_brick)
      continue

    assert previous_metabrick.date <= vacation_segment.start
    break
  else:
    # The vacation starts after the last brick of the road, so it actually
    # won't have any effect except to prolong the goal which we assume is
    # not intended.
    logging.debug("Got to the end of the YBR without needing this vacay")
    return result

  # At this point, next_brick is the first invalid brick we need to edit,
  # so next we'll scan ahead until we find the next valid brick.
  first_invalid_brick = next_brick
  first_invalid_index = index
  logging.debug("Found the first invalid brick: %s, %s",
                first_invalid_index, first_invalid_brick)

  first_rate_brick = first_invalid_brick if first_invalid_brick.rate is not None else None
  last_total_brick = first_invalid_brick if first_invalid_brick.total is not None else None
  first_valid_brick = None
  first_valid_index = None
  for index, next_brick in enumerate(road[first_invalid_index + 1:]):
    logging.debug("Walking the YBR to (%s, %s) looking for a valid brick",
                  index + first_invalid_index + 1, next_brick)
    if next_brick.date > vacation_segment.end:
      first_valid_brick = next_brick
      first_valid_index = index + first_invalid_index + 1
      logging.debug("Found the first valid brick after vacay ends: %s, %s",
                    first_valid_index, first_valid_brick)
      if last_total_brick is None and next_brick.total is not None:
        last_total_brick = next_brick
        logging.debug("Using this first valid brick as a total brick because "
                      "we haven't found one yet and we end inside it.")
      break
    if next_brick.total is not None:
      last_total_brick = next_brick
    elif first_rate_brick is None:
      first_rate_brick = next_brick
  else:
    if vacation_segment.end > next_brick.date:
      logging.debug("This vacation starts inside the YBR but ends outside it. "
                    "Trimming vacation_segment.end from %s to %s",
                    vacation_segment.end, next_brick.date)
      vacation_segment = vacation_segment._replace(end=next_brick.date)
    else:
      logging.debug("This vacation ends inside the last brick of the YBR.")

  # At this point, next_brick is the first valid brick after the vacation.
  # Time to process the range of bad bricks we found.
  logging.debug("Result so far (about to insert vacay): %s", result)
  logging.debug(
      "Inserting vacation using previous_metabrick: %s, first_rate_brick: %s, last_total_brick: %s, "
      "first_invalid_brick: %s, first_valid_brick: %s", previous_metabrick,
      first_rate_brick,
      last_total_brick, first_invalid_brick, first_valid_brick)

  if last_total_brick is None:
    logging.debug("Ignoring total handling since only rates are present.")
    result.append(Brick(vacation_segment.start, None, first_rate_brick.rate))
    result.append(Brick(vacation_segment.end, None, vacation_segment.rate))
    if first_invalid_brick.date > vacation_segment.end:
      result.append(first_invalid_brick)
  elif vacation_segment.total_handling == config_pb2.VacationPattern.DISCARD_TOTALS:
    logging.debug("Using handling DISCARD_TOTALS")
    #(d[s], -, (t - t[p]) / (d - d[p]))
    #(d[e], -, m')
    #(d, -, (t - t[p]) / (d - d[p])) # Omitted if d < d[e]
    rate = (ONE_DAY * (rate_seconds / ONE_DAY) * (last_total_brick.total - previous_metabrick.total) /
           (last_total_brick.date - previous_metabrick.date))
    logging.debug("Rate = %s" , rate)
    result.append(Brick(vacation_segment.start, None, rate))
    result.append(Brick(vacation_segment.end, None, vacation_segment.rate))
    if last_total_brick.date > vacation_segment.end:
      result.append(Brick(last_total_brick.date, None, rate))
  elif vacation_segment.total_handling == config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION:
    #(d[s], t[p] + (t - t[p]) / (d - d[p]) * (d[s] - d[p]), -)
    #(d[e], -, m')
    #(d, t, -) # Unless d < d[e], in which case replace d with d[e]+86400
    logging.debug("Using handling REACH_TOTAL_AFTER_VACATION")
    rate = ((last_total_brick.total - previous_metabrick.total) /
           (last_total_brick.date - previous_metabrick.date))
    logging.debug("Rate = %s" , rate * rate_seconds)
    result.append(Brick(
        vacation_segment.start,
        previous_metabrick.total +
        rate * (vacation_segment.start - previous_metabrick.date),
        None))
    result.append(Brick(vacation_segment.end, None, vacation_segment.rate))
    result.append(last_total_brick._replace(
        date=last_total_brick.date if
        last_total_brick.date > vacation_segment.end else
        vacation_segment.end + ONE_DAY))
  elif vacation_segment.total_handling == config_pb2.VacationPattern.REACH_TOTAL_BEFORE_VACATION:
    # (d[s], t[p] + (t - t[p]) / (d - d[p]) * (d[e] - d[p]), -)
    # (d[e], -, m')
    #(d, t, -) # Omitted if d < d[e]
    logging.debug("Using handling REACH_TOTAL_BEFORE_VACATION")
    if first_invalid_brick == Brick(vacation_segment.end, None, vacation_segment.rate):
      logging.debug("Found a brick that looks exactly like the vacation brick "
                    "in exactly the spot we'd like to put it. Aborting the "
                    "entire process now because otherwise we'll try to slurp "
                    "up the work to do to get to last_total_brick's total "
                    "every time this script is run.")
      # Note this is returning the original road with no edits, not result.
      return road

    rate = ((last_total_brick.total - previous_metabrick.total) /
           (last_total_brick.date - previous_metabrick.date))
    logging.debug("Rate = %s" , rate * rate_seconds)
    result.append(Brick(
        vacation_segment.start,
        previous_metabrick.total +
        rate * (vacation_segment.end - previous_metabrick.date),
        None))
    result.append(Brick(vacation_segment.end, None, vacation_segment.rate))
    if last_total_brick.date > vacation_segment.end:
      result.append(last_total_brick)
  else:
    raise "Unknown TotalHandling: %s" % vacation_segment.total_handling

  logging.debug("Result so far (about to extend): %s", result)
  # Now we've put the vacation in place, time to put in all the rest of the road
  # We discard any remaining bricks with inside the result, which is possible
  # when one of the total handlers wants to overwrite/replace the brick from
  # which it got the total.
  if first_valid_index is not None:
    result.extend([b for b in road[first_valid_index:] if b.date > result[-1].date])
  logging.debug("Result so far (about to compress): %s", result)
  assert result[0].date is not None and result[0].total is not None
  assert all(brick.date is not None for brick in result)
  result = compress_road(result)
  assert result[0].date is not None and result[0].total is not None
  assert all(brick.date is not None for brick in result)
  return result



def main():
  # data: A roadall matrix
  # error: Boolean, True iff this goal has had a read/write error at any point.
  Roadall = collections.namedtuple('Roadall', ['data', 'error'])
  # {goalname: Roadall}
  roads = collections.defaultdict(lambda: Roadall([], False))

  config = get_config('config')
  for vacation_entry in config.vacation_entry:
    for goalname in vacation_entry.goalname:
      for vacation_pattern in vacation_entry.vacation_pattern:
        if roads[goalname].error:
          continue

        if not roads[goalname].data:
          roads[goalname] = Roadall(*get_roadall(config.username, goalname))
        if roads[goalname].error:
          continue

        #roads[goalname] = Roadall(
        #    *build_fat_road(roads[goalname].data, vacation_pattern))

  for goalname, (fat_roadall, error) in roads.iteritems():
    if error:
      print 'Not updating road for %s due to previous errors.' % goalname
      continue
    roadall = compress_road(fat_roadall)
    print '%s: %s -- %s' % (goalname, error, roadall)


if True:
  logging.basicConfig(level=logging.DEBUG)

  data = get_roadall('drtall', 'testroadall2')
  road, runits, rah = data['roadall'], data['runits'], data['rah']
  print road, runits, rah
  new_road = apply_vacation_segment([Brick(*brick) for brick in road], runits, VacationSegment(1426003200, 1426867200, 0, config_pb2.VacationPattern.REACH_TOTAL_AFTER_VACATION))
  print new_road
  #new_road = insert_rah(new_road, rah)
  #print new_road
  if True:
    #mod('drtall', 'testroadall2', [[1424970000, 0, None], [1426608000, 500.0, None]])
    mod('drtall', 'testroadall2', new_road)

    road = get_roadall('drtall', 'testroadall2')
    print road