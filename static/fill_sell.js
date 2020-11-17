function fill_sell()
{
    var x = location.search;
    var sym = x.slice(6, -1);
    document.getElementById("symbol").value = sym;

}