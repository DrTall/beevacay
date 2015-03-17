DIY    = 365.25      # this is what physicists use, eg, to define a light year
SID    = 86400       # seconds in a day

SECS = { 'y' : DIY*SID,     # Number of seconds in a year, month, etc
         'm' : DIY/12*SID,
         'w' : 7*SID,
         'd' : SID,
         'h' : 3600         }

siru = SECS[runits] # seconds in rate units

# Helper for roadfunc. Return the value of the segment of the YBR at time x, 
# given the start of the previous segment (tprev,vprev) and the rate r. 
# (Equivalently we could've used the start and end points of the segment, 
# (tprev,vprev) and (t,v), instead of the rate.)
def rseg(tprev, vprev, r, x): 
  if exprd and r*(x-tprev) > 230: return 1e100 # bugfix: math overflow
  return vprev*exp(r*(x-tprev)) if exprd else vprev+r*(x-tprev)

# Take a full road matrix and a time t; return value of the centerline at time t
def roadfunc(road, x):
  if   x<road[0][0]: return road[0][1] # in case you want values before road start
  for i in range(1, len(road)):
    if x<road[i][0]: return rseg(road[i-1][0], road[i-1][1], road[i][2]/siru, x)
  return road[-1][1]