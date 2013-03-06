# -*- coding: utf-8 -*-
from xmlrpclib import ServerProxy
server = ServerProxy("http://ipchannels-frontend.integreen-life.bz.it/xmlRpcFrontEnd/xmlrpc")
#server = ServerProxy("http://xmlrpcfrontend.mapserver.tis.bz.it/xmlRpcFrontEnd/xmlrpc")
from datetime import datetime

def user(): return dict(form=auth())

@cache(request.env.path_info, time_expire=3600, cache_model=cache.ram)
def index():
	try:
		parks = __get_parks_info()
		return {'parks': parks}
	except Exception:
		return 'Data not available'

def trend():
	park_id = request.args(0) or 'index'
	if not(park_id and park_id.isdigit()): raise HTTP(404)
	parks = __get_parks_info()
	return {'parks': parks, 'park_id':park_id}

def parking():
	response.files.append(URL('static','js/OpenLayers.js'))
	park_id = request.args(0) or 'index'
	if not(park_id and park_id.isdigit()): raise HTTP(404)
	park = __get_park_data(int(park_id))
	response.title = "%s %s" %(T('Parking'), park['name'])
	response.meta.description = "%s %s" % (T('Map and number of free slots of the parking'), park['name'])
	response.menu.append( (T('Trend'), False, URL('default', 'trend', args=[park['park_id'], park['name']])))
	return {'park': park, 'park_id':park_id}

def map():
	response.files.append(URL('static','js/OpenLayers.js'))
	response.files.append(URL('static','js/controllers.js'))
	return {}

def doc():
	methods = server.system.listMethods()
	methods.sort()
	return {'server':server, 'methods':methods}

def get_history():
	if not(request.ajax): raise HTTP(403)
	park_id = request.args(0) or 'index'
	n_days = int(request.vars.interval) if request.vars.interval and request.vars.interval.isdigit() else 7
	if not(park_id and park_id.isdigit()): raise HTTP(404)
	data = server.DataManager.getFreeSlotsByTimeAndParkingArea(int(park_id), 24*60*n_days)
	output = []
	for element in data:
		epoch = (datetime.strptime(str(element[1]), "%Y%m%dT%H:%M:%S") - datetime(1970,1,1)).total_seconds() 
		milli_epoch = epoch * 1000
		output.append([milli_epoch,element[0]])
	return response.render('generic.json', {'park_%s' % park_id:{'data':output, 'park_id':park_id}})	
	
def freeslots():
	if not(request.ajax): raise HTTP(403)
	park_id = request.args(0) or 'index'
	if not(park_id and park_id.isdigit()): raise HTTP(404)
	data = __get_park_data(int(park_id))	
	json = {'freeslots':data['freeslots']}	

	freeslots = request.args(1) or 'index'
	if data['freeslots'] != -1 and (not(freeslots and freeslots.isdigit()) or int(freeslots) != data['freeslots']):
		json['plain_html'] = response.render('default/park_bar.html', park=data )

	return response.render('generic.json', json)

def __get_park_data(park):
	data = cache.ram('park_%s' % park, lambda: server.DataManager.getParkingStation(park), time_expire=3600)
	if not(isinstance(data, dict)): 
		cache.ram('park_%s' % park, lambda: None, time_expire=0)		
		raise HTTP(500)	
	data['park_id']	= park
	data['freeslots'] = server.DataManager.getNumberOfFreeSlots(park)
	name = data['name']
	try:
		data['name'] = name[name.index('-') + 1:].strip()
	except:
		data['name'] = name.strip()
	data['slots_taken'] = data['slots'] - data['freeslots']
	data['slots_taken_rate'] = (data['slots_taken'] * 100) / data['slots']
	data['freeslots_rate'] = 100 - data['slots_taken_rate']
	return data

def __get_parks_info():
	parks_id = cache.ram('parkingIds', lambda: server.DataManager.getParkingIds(), time_expire=3600)
	if parks_id == -1:
		return 'errore'
	parks = []
	for park in parks_id:
		data = __get_park_data(park)
		parks.append( data )
	return parks
