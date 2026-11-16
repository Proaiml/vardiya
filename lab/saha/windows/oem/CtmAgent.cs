// A stand-in for the Control-M agent on a Windows host: a real Windows service.
// It reads C:\ctm\agent.cfg (server=..., port=...). If the file is missing or the port is not a number the service
// refuses to start and says why in C:\ctm\logs\agent.log and in the Application event log. While it runs it writes
// a heartbeat line every 10 seconds; the lab reads the heartbeat to know the agent is "Available".
using System;
using System.Diagnostics;
using System.IO;
using System.ServiceProcess;
using System.Threading;

public class CtmAgent : ServiceBase
{
    const string Cfg = @"C:\ctm\agent.cfg";
    const string Log = @"C:\ctm\logs\agent.log";
    Timer timer;

    public CtmAgent() { ServiceName = "CtmAgent"; CanStop = true; }

    static void Write(string line)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Log));
        File.AppendAllText(Log, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " " + line + Environment.NewLine);
    }

    protected override void OnStart(string[] args)
    {
        string server = null; int port = -1;
        if (!File.Exists(Cfg))
        {
            Fail("CTM5101 yapilandirma dosyasi yok: " + Cfg);
        }
        foreach (var raw in File.ReadAllLines(Cfg))
        {
            var line = raw.Trim();
            if (line.StartsWith("server=")) server = line.Substring(7);
            if (line.StartsWith("port=") && !int.TryParse(line.Substring(5), out port)) Fail("CTM5102 gecersiz port degeri: '" + line.Substring(5) + "'");
        }
        if (string.IsNullOrEmpty(server) || port <= 0) Fail("CTM5103 server ya da port tanimli degil: " + Cfg);
        Write("ajan basladi; sunucu " + server + ":" + port);
        timer = new Timer(_ => Write("calisiyor"), null, 0, 10000);
    }

    void Fail(string why)
    {
        Write("BASLATILAMADI: " + why);
        try { EventLog.WriteEntry("CtmAgent", why, EventLogEntryType.Error); } catch { }
        throw new InvalidOperationException(why);
    }

    protected override void OnStop()
    {
        if (timer != null) timer.Dispose();
        Write("ajan durduruldu");
    }

    public static void Main() { ServiceBase.Run(new CtmAgent()); }
}
