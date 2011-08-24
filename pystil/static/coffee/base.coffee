class @Base

    constructor: (@elt) ->
        @elt.addClass 'loading'
        @criteria = @elt.attr("data-criteria").split(',')
        @fetch()

    fetch: () ->
        $.ajax
            url: @url()
            method: 'GET'
            dataType: 'json'
            success: @reply

    reply: (response) =>
        @elt.removeClass 'loading'
        if @criteria.length > 0
            @fetch()

    url: () ->
        site = location.pathname.split("/")[1]
        json = "/#{site}/#{@type}_by_#{@criteria.pop()}"
        if @stamp
            json += "_at_#{@stamp}"
        "#{json}.json"
