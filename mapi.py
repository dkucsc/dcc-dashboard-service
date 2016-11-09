from flask import Flask, jsonify, request
#import the FlaskElasticsearch package
from flask.ext.elasticsearch import Elasticsearch
#import json
import ast
#import the cors tools
from flask_cors import CORS, cross_origin
#import the flask functionality
import flask_excel as excel

app = Flask(__name__)
es = Elasticsearch()

#Assumption: objectId is download_id
#Parses the elasticSearch response 
def parse_ES_response(es_dict, the_size, the_from, the_sort, the_order):
	#print es_dict
	protoDict = {'hits':[]}
	for hit in es_dict['hits']['hits']:
		if '_source' in hit:
			protoDict['hits'].append(hit['_source'])
		#protoDict['hits'].append(hit['_source'])
		else:
			try:
				protoDict['hits'].append(hit['fields'])
			#protoDict['hits'].append(hit['fields'])
			except:
				pass
		#print hit
	#print protoDict

	protoDict['pagination'] = {
		'count' : len(es_dict['hits']['hits']),#25,
		'total' : es_dict['hits']['total'],
		'size' : the_size,
		'from' : the_from+1,
		'page' : (the_from/(the_size))+1, #(the_from/(the_size+1))+1
		'pages' : -(-es_dict['hits']['total'] // the_size),
		'sort' : the_sort,
		'order' : the_order
	}

	protoDict['termFacets'] = es_dict['aggregations']

	#func_total = lambda x: x+x
	#Get the total for all the terms
	for section in protoDict['termFacets']:
		m_sum = 0
		#print section
		for bucket in protoDict['termFacets'][section]['buckets']:
			m_sum += bucket['doc_count']
			#func_total(bucket['doc_count'])
		protoDict['termFacets'][section]['total'] = m_sum


	return protoDict
#This returns the agreggate terms and the list of hits from ElasticSearch
@app.route('/files/')
@cross_origin()
def get_data():
	print "I hate my life"
	#Get all the parameters from the URL
	m_field = request.args.get('field')
	m_filters = request.args.get('filters')
	m_From = request.args.get('from', 1, type=int)
	m_Size = request.args.get('size', 25, type=int)
	m_Sort = request.args.get('sort', 'center_name')
	m_Order = request.args.get('order', 'desc')

	#Will hold the query that will be used when calling ES
	mQuery = {}
	#Gets the index in [0 - (N-1)] form to communicate with ES
	m_From -= 1 
	#print m_filters
	#print dict(m_filters)
	#print m_filters['file']
	#get a list of all the fields requested
	try:
		m_fields_List = [x.strip() for x in m_field.split(',')]
	except:
		m_fields_List = None
	#print m_fields_List
	#Get a list of all the Filters requested
	try:
		m_filters = ast.literal_eval(m_filters)
		#filt_list = [{"match":{x:y['is'][0]}} for x,y in m_filters['file'].items()]
		#mQuery = {"bool":{"must":filt_list}}

		#Functions for calling the appropriates query filters
		onlyOne = lambda x,y: {x:{"query": y['is'][0]}}
		moreThanOne = lambda x,y: {x:{"query": ' '.join(y['is']), "operator": "or"}}
		matchValues = lambda x,y: moreThanOne(x, y) if len(y['is']) > 1 else onlyOne(x, y)
		filt_list = [{"match": matchValues(x, y)} for x,y in m_filters['file'].items()]
		mQuery = {"bool":{"must":[filt_list]}}
		#print filt_list	
		#print mQuery	
		#print m_filters['file']
		#pass
	except Exception, e:
		print str(e)
		m_filters = None
		mQuery = {"match_all":{}}
		pass
	mText = es.search(index='analysis_index', body={"query": mQuery, "aggs" : {
        "centerName" : {
            "terms" : { "field" : "center_name",
            			"min_doc_count" : 0,
                        "size" : 99999}           
        },
        "projectCode":{
            "terms":{
                "field" : "project",
                "min_doc_count" : 0,
                "size" : 99999
            }
        },
        "specimenType":{
            "terms":{
                "field" : "specimen_type",
                "min_doc_count" : 0,
                "size" : 99999
            }
        },
        "fileFormat":{
            "terms":{
                "field" : "file_type",
                "min_doc_count" : 0,
                "size" : 99999
            }
        },
        "workFlow":{
            "terms":{
                "field" : "workflow",
                "min_doc_count" : 0,
                "size" : 99999
            }
        },
        "analysisType":{
            "terms":{
                "field" : "analysis_type",
                "min_doc_count" : 0,
                "size" : 99999
            }
        }


    }, "fields":m_fields_List}, from_=m_From, size=m_Size, sort=m_Sort+":"+m_Order)
	#return jsonify(mText)
	return jsonify(parse_ES_response(mText, m_Size, m_From, m_Sort, m_Order))

#Get the manifest. You need to pass on the filters
@app.route('/files/export')
@cross_origin()
def get_manifest():
	m_filters = request.args.get('filters')
	m_Size = request.args.get('size', 25, type=int)
	mQuery = {}
	try:
		m_filters = ast.literal_eval(m_filters)
		#Functions for calling the appropriates query filters
		onlyOne = lambda x,y: {x:{"query": y['is'][0]}}
		moreThanOne = lambda x,y: {x:{"query": ' '.join(y['is']), "operator": "or"}}
		matchValues = lambda x,y: moreThanOne(x, y) if len(y['is']) > 1 else onlyOne(x, y)
		filt_list = [{"match": matchValues(x, y)} for x,y in m_filters['file'].items()]
		mQuery = {"bool":{"must":[filt_list]}}

	except Exception, e:
		print str(e)
		m_filters = None
		mQuery = {"match_all":{}}
		pass
	mText = es.search(index='analysis_index', body={"query": mQuery}, size=m_Size)

	protoList = []
	for hit in mText['hits']['hits']:
		if '_source' in hit:
			protoList.append(hit['_source'])
		#protoDict['hits'].append(hit['_source'])
	print protoList
	return excel.make_response_from_records(protoList, 'tsv', file_name = 'manifest')
	#return jsonify(mText)


#This will return a summary of the facets
@app.route('/files/facets')
@cross_origin()
def get_facets():
	#Search the aggregates.
	#Parse them
	#Return it as a JSON output.
	#Things I need to know: The final format of the indexes stored in ES
	return "Test"












