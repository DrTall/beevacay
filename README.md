# beevacay
Automatically schedule "take a break" for Beeminder goals for weekends/vacations

# Design
Ideally reading example_config and picking one that looks like what you want
would be enough for you to use this tool. However, if you go to build your own
config it's possible for some of the options to combine in surprising ways,
and since there is real money involved let's try to be thorough. 

## Gory details of road splitting
Let us define a **brick** to be a 3-tuple (d,t,m) corresponding to each
(date, total, rate) tuple in the roadall matrix. Let us define a **vacation
segment** to be a 3-tuple (d[s],d[e],m') where d[s] is the start date,
d[e] is the end date, and m' is the rate to apply. A vacation pattern is
broken into vacation segments of consecutive days where its rate applies. A
vacation pattern that omits the specific_weekday parameter will only have one
vacation segment.

A vacation segment will overlap one or more bricks in the existing road.
The types of bricks overlapped (in terms of which of their fields is
missing) determines the work that needs to be done.

### Dealing with Rates
If all of the overlapped bricks are of the form (d,-,m), then we select the
first such brick (d,-,m) and replace the range with three bricks as follows:

```
  (d[s], -, m)
  (d[e], -, m')
  (d, -, m)  # Omitted if d < d[e]
```

In essence, this means that the first rate that touches the vacation will be
preserved, and any rates specified during the vacation will be discarded.

Because the API forbids a (d,-,m) to begin the road, we don't need to worry
about upsetting the initial conditions of the road.

### Dealing with Totals
If any of the overlapped bricks are of the form (d,t,-), then we have a more
complex situation. This script takes totals seriously, to the point of treating
them like mini-commitments. For this case, we discard all (d,-,m) bricks in 
the range and focus only on the (d,t,-) brick(s).

In the event that there are multiple (d,t,-)
bricks overlapping the vacation, we take the last one to be authoritative.
This may lead to surprising behavior if your road is not monotonic, but I am
guessing that if you have super customized roads you are doing your own hacking.
Given this date & total brick (d,t,-) to honor, the handling is controlled by
the `total_handling` config parameter, as detailed below.

All of the handling options depend on the date and total of the previous brick,
**d[p]** and **t[p]**. We can obtain d[p] from the brick directly (because the API
guarantees any brick with a successor has a date), but in the general case t[p]
must be constructed by walking the yellow brick road forward from the lastest
brick with a total. We are guaranteed this is possible because the the API
requires a total on the first brick of the road.

#### REACH_TOTAL_BEFORE_VACATION
This is the default option. This option will adjust the rate of progress prior
to vacation so that the total you would have reached at the end of vacation is
instead reached at the start of the vacation. All of the work you would have
done during the vacation period is shifted to the front. Although this has the
potential to get you in hot water, it leaves your road dial untouched except
in the case where the vacation overlaps the end of the goal
(in which case your goal will actually finish sooner than planned).
This, like all the options, may make your road non-monotonic if you
specify a non-zero goal_rate in your vacation pattern.

Given the existing brick (d,t,-) and a (d[s], d[e], m') vacation to apply,
we replace the range with three bricks as follows:
```
  (d[s], t[p] + (t - t[p]) / (d - d[p]) * (d[e] - d[p]), -)
  (d[e], -, m')
  (d, t, -)  # Omitted if d < d[e]
```

#### DISCARD_TOTALS
If you've never given thought to whether your goal should specify a total or a
rate, or you otherwise don't place much emphasis on your totals, you may want
this option.

This option will ignore the requirement to meet any specified totals by their 
specified dates and instead maintain the average rate of progress you would have
needed to get to the specified total by the specified date as it was before the
insertion of the vacation.

Given this brick (d,t,-) and a (d[s], d[e], m')
vacation segment to apply, we replace the range with:

```
  (d[s], -, (t - t[p]) / (d - d[p]))
  (d[e], -, m')
  (d, -, (t - t[p]) / (d - d[p])) # Omitted if d < d[e]
```

#### REACH_TOTAL_AFTER_VACATION
This option will maintain the existing rate of progress before the vacation,
but still require that the specified total be reached by the goal date. 
Choosing the option that is most obviously akratic sounds tempting, but it is 
most likely to be surprising as well.

If the goal date falls inside the vacation, it is pushed to the day after the
vacation. This is likely to result in a steeper road segment after the vacation
ends. It may result in a more or less steep road segment before the vacation
if discarded (d,-,m) bricks existed prior to the (d,t,-) brick under
consideration -- this may even make your road non-monotonic if you specify
a non-zero goal_rate in your vacation pattern.

This option, when used repeatedly (as in weekends off) may result in a
cascading effect where the total work postponed from vacation is continually 
pushed towards the end of goal date, resulting in an arbitrarily steep final 
segment of the road, perhaps a long time in the future, or perhaps even making
your entire goal due in a single day.

Given the existing brick (d,t,-) and a (d[s], d[e], m') vacation to apply,
we replace the range with three bricks as follows:
```
  (d[s], t[p] + (t - t[p]) / (d - d[p]) * (d[s] - d[p]), -)
  (d[e], -, m')
  (d, t, -) # Unless d < d[e], in which case replace d with d[e]+86400
```

### Dealing with Dateless End Goals
The final case is editing a (-,t,r) brick. If a vacation segment overlaps this
brick, it is converted into a (d,t,-) brick using the API's mathishard and then
handled as in "Dealing with Rates" above. Then, we add the original (-,t,r) onto
the end of the road, which may make your road non-monotonic if you specified
a non-zero goal_Rate in your vacation pattern.