var book_data = null;
var amz_url = "http://www.amazon.com/dp/asin?tag=whotookmybook-20";
var availablePage = 2;
var noMoreAvailable=false;
var paging = true;
function borrower(book){
	return (available(book) ? "" : book.borrowed_by);
}

function return_link(book, link_text, tooltip){
	return '<a title="'+tooltip+'" href="/return/' + book.key + '">'+ link_text +'</a>';
}

function book_link(book){
	text = book.title;
	if(book.author != "unknown") text = text + " by " +   book.author; 
	if (book.asin && book.asin.length == 10) return  text + ' <a target="_blank" title="explore this book @ amazon" href="'+amz_url.replace("asin", book.asin)+'">'+'&#187;&#187;'+'</a>';
	return text;
}
oddOrEven = 'oddrow';
function toggleOddEven(){
	return oddOrEven == 'oddrow' ? oddOrEven = 'evenrow' : oddOrEven='oddrow';
}
/** ******************************************************************************* */
var myBooks = {

		empty: function(){
	$("#my_table").empty();
},

render_header: function(){
	$("#my_table").append('<thead><tr><th class="colone"></th><th class="coltwo">Book</th><th class="colthree">Lent to</th><th class="colfour"></th></tr></thead><tbody id="my_table_body"><tr/></tbody>');
},

render: function(books){
	myBooks.empty();
	if (books.length > 0) {
		myBooks.render_header();
		$.each(books, this.mybookrow);
	}
	else {
		$("#my_table").append('<tr class="nothing"><td>Nothing yet. Use the lookup box above to start adding to your collection.</td></tr>');
	}
},

del_link: function(book){
	return '<a href="/delete/' + book.key + '">delete</a>';
},

lend_link: function(book){
	return '<a href="/lend/' + book.key + '">lend</a>';
},

mybookrow: function(i){
	myBooks.newRow(this);
},

borrower: function(book){
	result = borrower(book);
	if(result != ""){
		result += "  " + return_link(book, "&#215;", "Not lent. I have this book with me.");
		result = "<a title='send gentle reminder email' href='#' class='reminder' name='"+book.key+"'>&#174;</a> " + result;
	}
	return result;
},

newRow: function(book){
	if ($("#my_table tr.nothing").length > 0) {
		myBooks.empty();
		myBooks.render_header();
	}
	$("#my_table_body tr:first").before("<tr id=" +	book.key +
			"\" class=\""+ toggleOddEven() +
			"\"><td>" + myBooks.del_link(book) + "</td><td>" + book_link(book) +
			"</td><td>" +
			myBooks.borrower(book) +
			"</td><td class='action'>" +
			myBooks.lend_link(book) +
	"</td></tr>");
},
lent_count: function(list){
	count = 0;
	if (list) {
		$.each(list, function(i){
			if (!available(this)) 
				count++;
		});
	}
	return count;
},

handle_event: function(event, book){
	if (event == "evt_book_added") {
		myBooks.newRow(book);
	}
}
};
/** ******************************************************************************* */
var borrowedBooks = {
		render: function(books){
	$("#borrowed_table").empty();
	if (books.length > 0) {
		$("#borrowed_table").append('<tr><th class="colone">From</th><th class="coltwo">Book</th><th class="colthree"></th><th class="colfour"></th></tr>');
		$.each(books, this.borrowedBookrow);
	}
	else {
		$("#borrowed_table").append('<tr class="nothing"><td>Nothing yet. Don&apos;t you want to read any of the available books?</td></tr>');
	}
},

borrowedBookrow: function(){
	$("#borrowed_table").append("<tr id=" + this.key +
			"\" class=\""+ toggleOddEven() +
			"\"><td>" + this.owner + "</td><td>" + book_link(this) +
			"</td><td></td><td class='action'>" +
			return_link(this, "return", "return book to owner") +
	"</td></tr>");
}
};
/** ******************************************************************************* */
function renderFriendsBooks(books){
	$("#hrefTabFriend").text("All books of "+currentFriend);
	$("#friend_table").empty();
	if (books.length > 0) {
		$("#friend_table").append('<tr><th class="coltwo">Book</th><th class="colthree">Lent to</th><th class="colfour"></th></tr>');
		$.each(books, friendBookRow);
	}
	else {
		$("#friend_table").append('<tr class="nothing"><td>No books yet.</td></tr>');
	}
}

function renderOtherBooks(books){
	var appendMode = false;
	if(arguments[1]==true) appendMode=true;
	if(!appendMode) $("#others_table").empty(); 
	if (books.length > 0) {
		if(!appendMode)
			$("#others_table").
			  append('<tr><th class="colone">Owner</th><th class="coltwo">Book</th><th class="colthree">Lent to</th><th class="colfour"></th></tr>');
		$.each(books, othersbookrow);
	}
	else {
		if(!appendMode)
			$("#others_table").append('<tr class="nothing"><td>No books found.</td></tr>');
		else
			noMoreAvailable = true;
	}
	$(".groupmbr").click(function(){
		showLoadingGif();
		currentFriend = $(this).text();
		booksOf($(this).attr('name'));
	});
}

function borrow_link(book){
	return available(book) ? '<a href="/borrow/' + book.key + '">borrow</a>' : "";
}

function othersbookrow(){
	$("#others_table").append(
			"<tr id=" + this.key  +
			" class=\""+ toggleOddEven()
			+"\"><td><a href=\"#\" class=\"groupmbr\" name=\""+
			this.owner_key+
			"\" title=\"see all books of "+ this.owner +
			"\">" + this.owner + "</a></td><td>" + book_link(this) +
			"</td><td>" +
			borrower(this) +
			"</td><td class='action'>" +
			borrow_link(this) +
	"</td></tr>");
}
function friendBookRow(){
	$("#friend_table").append(
			"<tr class=\""+ toggleOddEven()
			+"\"><td>" + book_link(this) +
			"</td><td>" +
			borrower(this) +
			"</td><td class='action'>" +
			borrow_link(this) +
	"</td></tr>");
}
/** ******************************************************************************* */
function showLoadingGif(){
	$('#overlay').show();
}

function hideLoadingGif(){
	$('#overlay').hide();
}

function updateBookCount(data){
	$("#book_count").empty();
	own_count = data['own_count'] ? data['own_count'] : 0
			borrow_count = data.borrowedBooks ? data.borrowedBooks.length : 0
					$("#book_count").append("<strong>Your book stats:</strong>&nbsp;&nbsp;<big class='bignum'> " + own_count + "</big> owned &nbsp;&nbsp; <big class='bignum'>" +
							myBooks.lent_count(data.mybooks) +
							"</big> lent&nbsp;&nbsp; <big class='bignum'>" +
							borrow_count +
					"</big> borrowed");
}

function available(book){
	return (book.borrowed_by == "None");
}

function showOwnedTab(){
	$("#tabOwned").css('background-color', highlight);
	$("#tabAvailable").css('background-color', silver);
	$("#tabBorrowed").css('background-color', silver);
	$("#tabFriend").css('background-color', silver);
	if (own_count > 25) $("#searchMineBar").show();
	$("#borrowed_div").hide();
	$("#others_div").hide();
	$("#friend_div").hide();
	$("#my_div").show();
	paging = false;
}
function showAvailableTab(){
	$("#tabAvailable").css('background-color', highlight);
	$("#tabBorrowed").css('background-color', silver);
	$("#tabOwned").css('background-color', silver);
	$("#tabFriend").css('background-color', silver);
	$("#my_div").hide();
	$("#borrowed_div").hide();
	$("#friend_div").hide();
	$("#others_div").show();
	paging = true;
	if(argument[0]==false) paging = false;//no pagination for search results
}
function showFriendsTab(){
	$("#tabFriend").css('background-color', highlight);
	$("#tabFriend").show();
	$("#tabAvailable").css('background-color', silver);
	$("#tabBorrowed").css('background-color', silver);
	$("#tabOwned").css('background-color', silver);
	$("#my_div").hide();
	$("#borrowed_div").hide();
	$("#others_div").hide();
	$("#friend_div").show();
	paging = false;
}


function renderBooks(data){
	book_data = data;
	updateBookCount(data);
	myBooks.render(data.mybooks);

	$("a.reminder").click(
			function(){
				cursor_wait();
				$.ajax({
					url: "/remind",
					type: "POST",
					data: {
					"book_id": $(this).attr('name')
				},
				success: function(){cursor_ok(); alert ('Reminder sent')},
				error: on_ajax_fail
				});				
			}
	); 


	borrowedBooks.render(data.borrowedBooks);
	renderOtherBooks(data.others);
	$("#borrowed_div").hide();
	$("#my_div").hide();
	silver = 'silver'; highlight = '#D9FFCC';
	$("#tabAvailable").css('background-color', highlight);
	$("#tabBorrowed").css('background-color', silver);
	$("#tabOwned").css('background-color', silver);
	$("#tabOwned").click(
			function(){
				showOwnedTab();
			}
	);
	$("#tabBorrowed").click(
			function(){
				$(this).css('background-color', highlight);
				$("#tabAvailable").css('background-color', silver);
				$("#tabOwned").css('background-color', silver);
				$("#tabFriend").css('background-color', silver);
				$("#others_div").hide();
				$("#my_div").hide();
				$("#friend_div").hide();
				$("#borrowed_div").show();
				paging = false;
			}
	);
	$("#tabAvailable").click(
			function(){
				showAvailableTab();
			}
	);
	$("#tabFriend").click(
			function(){
				showFriendsTab();
			}
	);
	hideLoadingGif();
}

function fetch_and_render_books(){
	showLoadingGif();
	$.ajax({
		url: "/mybooksj",
		type: "GET",
		success: renderBooks,
		errror: on_ajax_fail,
		dataType: "json"
	}); 
}

function on_add(book){
	myBooks.newRow(book);
	$("#my_table_body tr:first").css('background-color', '#D9FFCC');
	if (!book_data['mybooks']) {
		book_data['mybooks'] = [];
	}
	book_data['mybooks'].push(book);
	book_data['own_count'] += 1;
	updateBookCount(book_data);
	$("#book_title").val("");
	$("#book_author").val("");
	$("#suggestbox").focus();
	showOwnedTab();
	cursor_ok();
}

function on_ajax_fail(xhr, desc, exceptionobj){
	cursor_ok();
	if( xhr != null && (xhr.status === 400 || xhr.status === 412))
		alert(xhr.responseText);
	else
		alert("oops. Action failed. Please retry");
	hideLoadingGif();
}

function post_new_book(title, author, asin){
	cursor_wait();
	$("#suggestbox").val("");
	$.ajax({
		url: "/addBook",
		type: "POST",
		data: {
		"book_title": title,
		"book_author": author,
		"book_asin": asin
	},
	success: on_add,
	error: on_ajax_fail,
	dataType: "json"
	});
}

function onEnterDo(e, handler, arg){
	c = e.which ? e.which : e.keyCode;
	if (c == 13) {
		handler(arg);
		return false;
	}
	return true;
}

function changeNickname(newNick){
	showLoadingGif();
	$.ajax({
		url: "/nickname",
		type: "POST",
		data: {
		"new_nick": newNick
	},
	success: function(msg){
		$("#nick_text").hide();
		$("#hi_msg").text("Hi " + newNick);
	},
	error: on_ajax_fail
	});
	hideLoadingGif();
}

function booksOf(friend_key){
	$.ajax({
		url: "/booksof/"+friend_key,
		type: "GET",
		success: function(books){
		renderFriendsBooks(books); showFriendsTab();
		hideLoadingGif();
	},
	error: on_ajax_fail,
	dataType: "json"
	});
}

function myall(){
	$.ajax({
		url: "/booksof/"+book_data.user.key,
		type: "GET",
		success: function(books){
			myBooks.render(books);
			$("#showAllMyBooks").hide();
			hideLoadingGif();
		},
		error: on_ajax_fail,
		dataType: "json"
	});
}

function searchAvailable(term){
	if(term.length < 4){
		alert("search term should be at least 4 characters long!");
		return;
	}
	$("#search_progress").show();
	$.ajax({
		url: "/search",
		type: "POST",
		data: {"term": term},
		success: function(books){
			$("#search_progress").hide();
			renderOtherBooks(books); showAvailableTab(false);
		},
		error: on_ajax_fail,
		dataType: "json"
	});
}

function searchMine(term){
	$("#searchmine_progress").show();
	$.ajax({
		url: "/search",
		type: "POST",
		data: {
		"term": term,
		"whose": 'mine'
	},
	success: function(books){
		$("#searchmine_progress").hide();
		myBooks.render(books); showOwnedTab();
	},
	error: on_ajax_fail,
	dataType: "json"
	});
}

function loadMore(){
	if (noMoreAvailable) return;
	$("#paging_progress").show();
	$.ajax({
		url: "/friendsbooks" + book_data.user.key + '/' + (availablePage++),
		type: "GET",
		success: function(books){
		renderOtherBooks(books, true);
		$("#paging_progress").hide();
	},
	error: on_ajax_fail,
	dataType: "json"
	});
}
function setup_handlers(){
	var options = {
			script: "/lookup_amz?",
			varname: "fragment",
			json: true,
			callback: function(obj){
				showLoadingGif();
				post_new_book(obj.value, obj.info, obj.id);
				hideLoadingGif();
			}
	};
	new bsn.AutoSuggest('suggestbox', options);

	$("#btn_add_book").click(function(){
		showLoadingGif();
		post_new_book($("#book_title").val(), $("#book_author").val(), 0);
		hideLoadingGif();
	});

	$("#edit_nick").click(function(){
		$(this).hide();
		$("#nick_text").show().focus();
	});

	$("#nick_text").keypress(function(e){
		onEnterDo(e, changeNickname, jQuery(this).val());
	});

	$("#search").keypress(function(e){
		onEnterDo(e, searchAvailable, jQuery(this).val());
	});

	$("#searchmine").keypress(function(e){
		onEnterDo(e, searchMine, jQuery(this).val());
	});
	$("#showAllMyBooks").click(function(){
		showLoadingGif();
		myall();
	});

	$(window).scroll(function() {//from:http://blog.wekeroad.com/2009/11/27/paging-records-sucks--use-jquery-to-scroll-just-in-time
	    if(!paging) return;
		var gap = $(document).height() - $(window).height() - $(window).scrollTop();
		if (gap < 2) {
	        loadMore();
	    }
	});
	
}// end setup handlers

function cursor_wait(){
	document.body.style.cursor = 'wait';
}
function cursor_ok(){
	document.body.style.cursor = 'default';
}
function addOverlay(){
	// script from: http://www.sitepoint.com/forums/showthread.php?t=581377
	// loading.gif from http://www.ajaxload.info/

	$('<div id="overlay"/>').css({
		position: 'fixed',
		top: 0,
		left: 0,
		width: '100%',
		height: $(window).height() + 'px',
		background: 'white url(/s/loading.gif) no-repeat center'
	}).appendTo('body');	
}
$(document).ready(function(){
	addOverlay();
	$("#nick_text").hide();
	$("#tabFriend").hide();
	$("#manual").hide();
	$("#lookup_progress").hide();
	$("#search_progress").hide();
	$("#searchmine_progress").hide();
	$("#paging_progress").hide();
	$("#searchMineBar").hide();
	$("#show_manual").click(function(){
		$("#show_manual_span").hide();
		$("#manual").show();
		$("#book_title").focus();
	});
	fetch_and_render_books();
	setup_handlers();
	cursor_ok();
});
/** *********************************************************************************** */
/** *********************************************************************************** */
/**
 * author: Timothy Groves - http://www.brandspankingnew.net version: 1.2 -
 * 2006-11-17 1.3 - 2006-12-04 2.0 - 2007-02-07 2.1.1 - 2007-04-13 2.1.2 -
 * 2007-07-07 2.1.3 - 2007-07-19
 * 
 */


if (typeof(bsn) == "undefined")
	_b = bsn = {};


if (typeof(_b.Autosuggest) == "undefined")
	_b.Autosuggest = {};
else
	alert("Autosuggest is already set!");












_b.AutoSuggest = function (id, param)
{
	// no DOM - give up!
	//
	if (!document.getElementById)
		return 0;




	// get field via DOM
	//
	this.fld = _b.DOM.gE(id);

	if (!this.fld)
		return 0;




	// init variables
	//
	this.sInp 	= "";
	this.nInpC 	= 0;
	this.aSug 	= [];
	this.iHigh 	= 0;




	// parameters object
	//
	this.oP = param ? param : {};

	// defaults
	//
	var k, def = {
			minchars: 4,
			meth: "get",
			varname: "input",
			className: "autosuggest",
			timeout: 4000,
			delay: 200,
			offsety: -5,
			shownoresults: true,
			noresults: "No results!",
			maxheight: 250,
			cache: true,
			maxentries: 10
	};
	for (k in def)
	{
		if (typeof(this.oP[k]) != typeof(def[k]))
			this.oP[k] = def[k];
	}


	// set keyup handler for field
	// and prevent autocomplete from client
	//
	var p = this;

	// NOTE: not using addEventListener because UpArrow fired twice in Safari
	// _b.DOM.addEvent( this.fld, 'keyup', function(ev){ return
	// pointer.onKeyPress(ev); } );

	this.fld.onkeypress 	= function(ev){ return p.onKeyPress(ev); };
	this.fld.onkeyup 		= function(ev){ return p.onKeyUp(ev); };

	this.fld.setAttribute("autocomplete","off");
};
















_b.AutoSuggest.prototype.onKeyPress = function(ev)
{

	var key = (window.event) ? window.event.keyCode : ev.keyCode;



	// set responses to keydown events in the field
	// this allows the user to use the arrow keys to scroll through the results
	// ESCAPE clears the list
	// TAB sets the current highlighted value
	//
	var RETURN = 13;
	var TAB = 9;
	var ESC = 27;

	var bubble = 1;

	switch(key)
	{
	case RETURN:
		this.setHighlightedValue();
		bubble = 0;
		break;

	case ESC:
		this.clearSuggestions();
		break;
	}

	return bubble;
};



_b.AutoSuggest.prototype.onKeyUp = function(ev)
{
	var key = (window.event) ? window.event.keyCode : ev.keyCode;



	// set responses to keydown events in the field
	// this allows the user to use the arrow keys to scroll through the results
	// ESCAPE clears the list
	// TAB sets the current highlighted value
	//

	var ARRUP = 38;
	var ARRDN = 40;

	var bubble = 1;

	switch(key)
	{


	case ARRUP:
		this.changeHighlight(key);
		bubble = 0;
		break;


	case ARRDN:
		this.changeHighlight(key);
		bubble = 0;
		break;


	default:
		this.getSuggestions(escape(this.fld.value));
	}

	return bubble;


};








_b.AutoSuggest.prototype.getSuggestions = function (val)
{

	// if input stays the same, do nothing
	//
	if (val == this.sInp)
		return 0;


	// kill list
	//
	_b.DOM.remE(this.idAs);


	this.sInp = val;


	// input length is less than the min required to trigger a request
	// do nothing
	//
	if (val.length < this.oP.minchars)
	{
		this.aSug = [];
		this.nInpC = val.length;
		return 0;
	}




	var ol = this.nInpC; // old length
	this.nInpC = val.length ? val.length : 0;



	// if caching enabled, and user is typing (ie. length of input is
	// increasing)
	// filter results out of aSuggestions from last request
	//
	var l = this.aSug.length;
	if (this.nInpC > ol && l && l<this.oP.maxentries && this.oP.cache)
	{
		var arr = [];
		for (var i=0;i<l;i++)
		{
			if (this.aSug[i].value.substr(0,val.length).toLowerCase() == val.toLowerCase())
				arr.push( this.aSug[i] );
		}
		this.aSug = arr;

		this.createList(this.aSug);



		return false;
	}
	else
		// do new request
		//
	{
		$("#lookup_progress").show();
		var pointer = this;
		var input = this.sInp;
		clearTimeout(this.ajID);
		this.ajID = setTimeout( function() { pointer.doAjaxRequest(input) }, this.oP.delay );
	}

	return false;
};





_b.AutoSuggest.prototype.doAjaxRequest = function (input)
{
	// check that saved input is still the value of the field
	//
	if (input != escape(this.fld.value))
		return false;


	var pointer = this;


	// create ajax request
	//
	if (typeof(this.oP.script) == "function")
		var url = this.oP.script(encodeURIComponent(this.sInp));
	else
		var url = this.oP.script+this.oP.varname+"="+encodeURIComponent(this.sInp);

	if (!url)
		return false;

	var meth = this.oP.meth;
	var input = this.sInp;

	var onSuccessFunc = function (req) { pointer.setSuggestions(req, input) };
	var onErrorFunc = function (status) { alert("AJAX error: "+status); };

	var myAjax = new _b.Ajax();
	myAjax.makeRequest( url, meth, onSuccessFunc, onErrorFunc );
};





_b.AutoSuggest.prototype.setSuggestions = function (req, input)
{
	// if field input no longer matches what was passed to the request
	// don't show the suggestions
	//
	if (input != escape(this.fld.value))
		return false;


	this.aSug = [];


	if (this.oP.json)
	{
		var jsondata = eval('(' + req.responseText + ')');

		for (var i=0;i<jsondata.results.length;i++)
		{
			this.aSug.push(  { 'id':jsondata.results[i].id, 'value':jsondata.results[i].value, 'info':jsondata.results[i].info }  );
		}
	}
	else
	{

		var xml = req.responseXML;

		// traverse xml
		//
		var results = xml.getElementsByTagName('results')[0].childNodes;

		for (var i=0;i<results.length;i++)
		{
			if (results[i].hasChildNodes())
				this.aSug.push(  { 'id':results[i].getAttribute('id'), 'value':results[i].childNodes[0].nodeValue, 'info':results[i].getAttribute('info') }  );
		}

	}

	this.idAs = "as_"+this.fld.id;


	this.createList(this.aSug);

};














_b.AutoSuggest.prototype.createList = function(arr)
{
	var pointer = this;




	// get rid of old list
	// and clear the list removal timeout
	//
	_b.DOM.remE(this.idAs);
	this.killTimeout();


	// if no results, and shownoresults is false, do nothing
	//
	if (arr.length == 0 && !this.oP.shownoresults)
		return false;


	// create holding div
	//
	var div = _b.DOM.cE("div", {id:this.idAs, className:this.oP.className});	

	var hcorner = _b.DOM.cE("div", {className:"as_corner"});
	var hbar = _b.DOM.cE("div", {className:"as_bar"});
	var header = _b.DOM.cE("div", {className:"as_header"});
	header.appendChild(hcorner);
	header.appendChild(hbar);
	div.appendChild(header);




	// create and populate ul
	//
	var ul = _b.DOM.cE("ul", {id:"as_ul"});




	// loop throught arr of suggestions
	// creating an LI element for each suggestion
	//
	for (var i=0;i<arr.length;i++)
	{
		// format output with the input enclosed in a EM element
		// (as HTML, not DOM)
		//
		var val = arr[i].value;
		var st = val.toLowerCase().indexOf( this.sInp.toLowerCase() );
		var output = val.substring(0,st) + "<em>" + val.substring(st, st+this.sInp.length) + "</em>" + val.substring(st+this.sInp.length);


		var span 		= _b.DOM.cE("span", {}, output, true);
		if (arr[i].info != "")
		{
			var br			= _b.DOM.cE("br", {});
			span.appendChild(br);
			var small		= _b.DOM.cE("small", {}, arr[i].info);
			span.appendChild(small);
		}

		var a 			= _b.DOM.cE("a", { href:"#" });

		var tl 		= _b.DOM.cE("span", {className:"tl"}, " ");
		var tr 		= _b.DOM.cE("span", {className:"tr"}, " ");
		a.appendChild(tl);
		a.appendChild(tr);

		a.appendChild(span);

		a.name = i+1;
		// a.id = "asa_" + (i+1);
		a.onclick = function () { pointer.setHighlightedValue(); return false; };
		a.onmouseover = function () { pointer.setHighlight(this.name); };

		var li = _b.DOM.cE(  "li", {}, a  );

		ul.appendChild( li );
	}


	// no results
	//
	if (arr.length == 0 && this.oP.shownoresults)
	{
		var li = _b.DOM.cE(  "li", {className:"as_warning"}, this.oP.noresults  );
		ul.appendChild( li );
	}


	div.appendChild( ul );


	var fcorner = _b.DOM.cE("div", {className:"as_corner"});
	var fbar = _b.DOM.cE("div", {className:"as_bar"});
	var footer = _b.DOM.cE("div", {className:"as_footer"});
	footer.appendChild(fcorner);
	footer.appendChild(fbar);
	div.appendChild(footer);



	// get position of target textfield
	// position holding div below it
	// set width of holding div to width of field
	//
	var pos = _b.DOM.getPos(this.fld);

	div.style.left 		= pos.x + "px";
	div.style.top 		= ( pos.y + this.fld.offsetHeight + this.oP.offsety ) + "px";
	div.style.width 	= (this.fld.offsetWidth * 3) + "px";



	// set mouseover functions for div
	// when mouse pointer leaves div, set a timeout to remove the list after an
	// interval
	// when mouse enters div, kill the timeout so the list won't be removed
	//
	div.onmouseover 	= function(){ pointer.killTimeout() };
	div.onmouseout 		= function(){ pointer.resetTimeout() };


	// add DIV to document
	//
	document.getElementsByTagName("body")[0].appendChild(div);



	// currently no item is highlighted
	//
	this.iHigh = 0;


	$("#lookup_progress").hide();



	// remove list after an interval
	//
	var pointer = this;
	this.toID = setTimeout(function () { pointer.clearSuggestions() }, this.oP.timeout);
};















_b.AutoSuggest.prototype.changeHighlight = function(key)
{	
	var list = _b.DOM.gE("as_ul");
	if (!list)
		return false;

	var n;

	if (key == 40)
		n = this.iHigh + 1;
	else if (key == 38)
		n = this.iHigh - 1;


	if (n > list.childNodes.length)
		n = list.childNodes.length;
	if (n < 1)
		n = 1;


	this.setHighlight(n);
};



_b.AutoSuggest.prototype.setHighlight = function(n)
{
	var list = _b.DOM.gE("as_ul");
	if (!list)
		return false;

	if (this.iHigh > 0)
		this.clearHighlight();

	this.iHigh = Number(n);

	list.childNodes[this.iHigh-1].className = "as_highlight";


	this.killTimeout();
};


_b.AutoSuggest.prototype.clearHighlight = function()
{
	var list = _b.DOM.gE("as_ul");
	if (!list)
		return false;

	if (this.iHigh > 0)
	{
		list.childNodes[this.iHigh-1].className = "";
		this.iHigh = 0;
	}
};


_b.AutoSuggest.prototype.setHighlightedValue = function ()
{
	if (this.iHigh)
	{
		this.sInp = this.fld.value = this.aSug[ this.iHigh-1 ].value;

		// move cursor to end of input (safari)
		//
		this.fld.focus();
		if (this.fld.selectionStart)
			this.fld.setSelectionRange(this.sInp.length, this.sInp.length);


		this.clearSuggestions();

		// pass selected object to callback function, if exists
		//
		if (typeof(this.oP.callback) == "function")
			this.oP.callback( this.aSug[this.iHigh-1] );
	}
};













_b.AutoSuggest.prototype.killTimeout = function()
{
	clearTimeout(this.toID);
};

_b.AutoSuggest.prototype.resetTimeout = function()
{
	clearTimeout(this.toID);
	var pointer = this;
	this.toID = setTimeout(function () { pointer.clearSuggestions() }, 1000);
};







_b.AutoSuggest.prototype.clearSuggestions = function ()
{
	this.killTimeout();
	_b.DOM.remE(this.idAs);
};




//AJAX PROTOTYPE _____________________________________________


if (typeof(_b.Ajax) == "undefined")
	_b.Ajax = {};



_b.Ajax = function ()
{
	this.req = {};
	this.isIE = false;
};



_b.Ajax.prototype.makeRequest = function (url, meth, onComp, onErr)
{

	if (meth != "POST")
		meth = "GET";

	this.onComplete = onComp;
	this.onError = onErr;

	var pointer = this;

	// branch for native XMLHttpRequest object
	if (window.XMLHttpRequest)
	{
		this.req = new XMLHttpRequest();
		this.req.onreadystatechange = function () { pointer.processReqChange() };
		this.req.open("GET", url, true); //
		this.req.send(null);
		// branch for IE/Windows ActiveX version
	}
	else if (window.ActiveXObject)
	{
		this.req = new ActiveXObject("Microsoft.XMLHTTP");
		if (this.req)
		{
			this.req.onreadystatechange = function () { pointer.processReqChange() };
			this.req.open(meth, url, true);
			this.req.send();
		}
	}
};


_b.Ajax.prototype.processReqChange = function()
{

	// only if req shows "loaded"
	if (this.req.readyState == 4) {
		// only if "OK"
		if (this.req.status == 200)
		{
			this.onComplete( this.req );
		} else {
			this.onError( this.req.status );
		}
	}
};










//DOM PROTOTYPE _____________________________________________


if (typeof(_b.DOM) == "undefined")
	_b.DOM = {};



/* create element */
_b.DOM.cE = function ( type, attr, cont, html )
{
	var ne = document.createElement( type );
	if (!ne)
		return 0;

	for (var a in attr)
		ne[a] = attr[a];

	var t = typeof(cont);

	if (t == "string" && !html)
		ne.appendChild( document.createTextNode(cont) );
	else if (t == "string" && html)
		ne.innerHTML = cont;
	else if (t == "object")
		ne.appendChild( cont );

	return ne;
};



/* get element */
_b.DOM.gE = function ( e )
{
	var t=typeof(e);
	if (t == "undefined")
		return 0;
	else if (t == "string")
	{
		var re = document.getElementById( e );
		if (!re)
			return 0;
		else if (typeof(re.appendChild) != "undefined" )
			return re;
		else
			return 0;
	}
	else if (typeof(e.appendChild) != "undefined")
		return e;
	else
		return 0;
};



/* remove element */
_b.DOM.remE = function ( ele )
{
	var e = this.gE(ele);

	if (!e)
		return 0;
	else if (e.parentNode.removeChild(e))
		return true;
	else
		return 0;
};



/* get position */
_b.DOM.getPos = function ( e )
{
	var e = this.gE(e);

	var obj = e;

	var curleft = 0;
	if (obj.offsetParent)
	{
		while (obj.offsetParent)
		{
			curleft += obj.offsetLeft;
			obj = obj.offsetParent;
		}
	}
	else if (obj.x)
		curleft += obj.x;

	var obj = e;

	var curtop = 0;
	if (obj.offsetParent)
	{
		while (obj.offsetParent)
		{
			curtop += obj.offsetTop;
			obj = obj.offsetParent;
		}
	}
	else if (obj.y)
		curtop += obj.y;

	return {x:curleft, y:curtop};
};










//FADER PROTOTYPE _____________________________________________



if (typeof(_b.Fader) == "undefined")
	_b.Fader = {};





_b.Fader = function (ele, from, to, fadetime, callback)
{	
	if (!ele)
		return 0;

	this.e = ele;

	this.from = from;
	this.to = to;

	this.cb = callback;

	this.nDur = fadetime;

	this.nInt = 50;
	this.nTime = 0;

	var p = this;
	this.nID = setInterval(function() { p._fade() }, this.nInt);
};




_b.Fader.prototype._fade = function()
{
	this.nTime += this.nInt;

	var ieop = Math.round( this._tween(this.nTime, this.from, this.to, this.nDur) * 100 );
	var op = ieop / 100;

	if (this.e.filters) // internet explorer
	{
		try
		{
			this.e.filters.item("DXImageTransform.Microsoft.Alpha").opacity = ieop;
		} catch (e) { 
			// If it is not set initially, the browser will throw an error. This
			// will set it if it is not set yet.
			this.e.style.filter = 'progid:DXImageTransform.Microsoft.Alpha(opacity='+ieop+')';
		}
	}
	else // other browsers
	{
		this.e.style.opacity = op;
	}


	if (this.nTime == this.nDur)
	{
		clearInterval( this.nID );
		if (this.cb != undefined)
			this.cb();
	}
};



_b.Fader.prototype._tween = function(t,b,c,d)
{
	return b + ( (c-b) * (t/d) );
};