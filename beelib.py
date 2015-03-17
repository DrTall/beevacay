#!/usr/bin/python

######## blatantly hacky. should be refactored and put somewhere else. ########
 
def legal_road_change_or_err(user,goal,road):
  # ignores road width, because we have not thought enough about road width yet
  #! uncertain if works properly at today and the akrasia horizon
  #! likely to break on insufficiently normal time zones
  if not road or not road_is_a_road_matrix(road):
     return "that doesn't look like a road matrix", None
  from = road_matrix_to_pieces(goal.road_all)
  to = road_matrix_to_pieces(road)
 
  #! we should probably be validating the api input more heavily. and maybe doing that somewhere other than here.
  #if to[0][:type] != "valuedate"; return ["first road row must be [date,value,null]",nil]; end
  #if to[0...-1].any?{|v| v[:type] == "ratevalue"}; return ["only the last road row may be [null,value,rate]",nil]; end
  #if user.try(:admin); return [nil,true]; end #! should also check to make sure goal isn't one of user's non-test goals
  #if goal.exprd; return ["exponential road validation not implemented",nil]; end
 
  today = urtu(goal.bb[:tcur])
  eps = 0.000000001 # floating point epsilon
  # run a diff on the roads and return a list of days with the akrasia horizon at which the road is easier
  t = (0..7).map{|v| today + v}
    .map{|v| {date: v, from: road_front_center_at(from,v,goal.siru), to: road_front_center_at(to,v,goal.siru)}}
    .select{|v| goal.yaw == 1 ? v[:to] + eps < v[:from] : v[:from] + eps < v[:to]}
  t.empty? ? [nil,true] : ["illegal: may not make road easier before akrasia horizon - tried with #{t}"]; end
 
def road_is_a_road_matrix(road)
  return false if !road.is_a?(Array)
  road.each{|row| return false if !validrow(row) }
  true; end
 
def validrow(r)
  return false if not r.is_a?(Array) or r.size != 3
  return (r[0].nil?           and r[1].is_a?(Numeric) and r[2].is_a?(Numeric)) ||
         (r[0].is_a?(Numeric) and r[1].nil?           and r[2].is_a?(Numeric)) ||
         (r[0].is_a?(Numeric) and r[1].is_a?(Numeric) and r[2].nil?)
end
 
def road_matrix_to_pieces(road); road.map{|v|
  !v[1] ? {:type=>"ratedate", :rate=>v[2], :end=>v[0]} :
  !v[2] ? {:type=>"valuedate", :endv=>v[1], :end=>v[0]} :
    {:type=>"ratevalue", :rate=>v[2], :endv=>v[1]} }; end
 
def road_front_center_at(road,ud8d_date,siru)
  # has same sketchy behavior as roadfunc has - returns the frontmost point on discontinuities
  start = urtu(road[0][:end]); val = road[0][:endv]
  if ud8d_date >= start; road[1..-1].each do |v|
    if (v[:type]=="ratedate" || v[:type]=="valuedate") && urtu(v[:end]) < ud8d_date; val = road_segment_endv(v,start,val,siru); start = urtu(v[:end])
    else; val += road_segment_rate(v,start,val,siru) * (ud8d_date - start); break; end
  end; end; val; end
 
def road_segment_rate(v,start,startv,siru); v[:type]=="ratedate" || v[:type]=="ratevalue" ? (v[:rate]+0.0)/(siru/86400) : (v[:endv]+0.0-startv) / (urtu(v[:end])-start) ; end
def road_segment_endv(v,start,startv,siru):
  v[:type]=="ratevalue"|| v[:type]=="valuedate" ? v[:endv]+0.0 : startv + (v[:rate]+0.0)/(siru/86400) * (urtu(v[:end])-start) ; end
 
def unixandtwothirdsdate_round_to_unixdiv86400date(v):
  return (v-86400*2/3+86400/2) / 86400
def urtu(v):
  return unixandtwothirdsdate_round_to_unixdiv86400date(v)


