-- process.lua


function node_function()

end

function way_function()
	local highway = Find("highway")
	local building = Find("building")

	if highway ~= "" then
		Layer("transportation", false)
		Attribute("name", Find("name"))
		Attribute("class", highway)
	end

	if building ~= "" then
		Layer("building", true)
	end
end